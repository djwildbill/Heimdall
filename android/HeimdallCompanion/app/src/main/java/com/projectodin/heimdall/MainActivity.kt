package com.projectodin.heimdall

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.UUID
import java.util.concurrent.Executors

class MainActivity : ComponentActivity() {
    private val io = Executors.newSingleThreadExecutor()
    private val sppUuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
    private var socket: BluetoothSocket? = null
    private var reader: BufferedReader? = null

    private var uiState by mutableStateOf(JoshUiState())

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        if (result[Manifest.permission.BLUETOOTH_CONNECT] == true) connectJosh()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                JoshScreen(
                    state = uiState,
                    onConnect = { ensurePermissionThenConnect() },
                    onRefresh = { send("wifi-dashboard") },
                    onDoctor = { send("doctor") },
                    onCheckUpdate = { send("check-update") }
                )
            }
        }
        ensurePermissionThenConnect()
    }

    private fun ensurePermissionThenConnect() {
        if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED) {
            connectJosh()
        } else {
            permissionLauncher.launch(arrayOf(
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.BLUETOOTH_SCAN
            ))
        }
    }

    @Suppress("MissingPermission")
    private fun connectJosh() {
        uiState = uiState.copy(connection = "CONNECTING", message = "Looking for Josh…")
        io.execute {
            try {
                socket?.close()
                val manager = getSystemService(BluetoothManager::class.java)
                val adapter: BluetoothAdapter = manager.adapter ?: error("Bluetooth unavailable")
                val device: BluetoothDevice = adapter.bondedDevices.firstOrNull {
                    val name = it.name ?: ""
                    name.equals("HEIMDALL", true) ||
                        name.equals("JOSH-OVN-002", true) ||
                        name.contains("JOSH", true)
                } ?: error("Pair HEIMDALL / JOSH-OVN-002 in Android Bluetooth settings first")

                adapter.cancelDiscovery()
                val s = device.createRfcommSocketToServiceRecord(sppUuid)
                s.connect()
                socket = s
                reader = BufferedReader(InputStreamReader(s.inputStream))
                val hello = reader!!.readLine()
                runOnUiThread {
                    uiState = uiState.copy(
                        connection = "CONNECTED",
                        face = "(≖‿‿≖)",
                        message = "Opening the Bifrost…",
                        raw = hello
                    )
                }
                send("wifi-dashboard")
            } catch (e: Exception) {
                runOnUiThread {
                    uiState = uiState.copy(
                        connection = "DISCONNECTED",
                        face = "(-__-)",
                        message = e.message ?: e.toString()
                    )
                }
            }
        }
    }

    private fun send(cmd: String) {
        io.execute {
            try {
                val s = socket ?: error("Josh is not connected")
                val request = JSONObject().put("cmd", cmd).toString() + "\n"
                s.outputStream.write(request.toByteArray())
                s.outputStream.flush()
                val response = reader?.readLine() ?: error("No response from Josh")
                val json = JSONObject(response)
                runOnUiThread { render(cmd, json) }
            } catch (e: Exception) {
                runOnUiThread { uiState = uiState.copy(message = e.message ?: e.toString()) }
            }
        }
    }

    private fun render(cmd: String, json: JSONObject) {
        when {
            cmd == "wifi-dashboard" && json.optBoolean("ok") -> renderDashboard(json)
            cmd == "status" && json.optBoolean("ok") -> {
                val radio = json.optJSONObject("radio")
                val currentMode = radio?.optString("mode", "--") ?: "--"
                uiState = uiState.copy(
                    node = json.optString("node", "OVN-002"),
                    codename = json.optString("codename", "Josh"),
                    mode = currentMode.uppercase(),
                    raw = json.toString(2)
                )
            }
            else -> {
                uiState = uiState.copy(
                    message = json.optString("output", if (json.optBoolean("ok")) "Command completed" else json.optString("error", "Command failed")),
                    raw = json.toString(2)
                )
            }
        }
    }

    private fun renderDashboard(json: JSONObject) {
        val status = json.optJSONObject("status") ?: JSONObject()
        val list = mutableListOf<WifiNetwork>()
        val networksJson = json.optJSONArray("networks")
        if (networksJson != null) {
            for (i in 0 until networksJson.length()) {
                val n = networksJson.optJSONObject(i) ?: continue
                list += WifiNetwork(
                    ssid = n.optString("ssid", "(hidden)"),
                    channel = n.optString("channel", "--"),
                    signal = n.optInt("signal", 0),
                    security = n.optString("security", "Unknown")
                )
            }
        }

        val visible = status.optInt("observed_networks", list.size)
        val scan = status.optInt("scan_number", 0)
        val mode = status.optString("mode", "live").uppercase()
        val error = status.optString("last_inventory_error", "")
        val face = when {
            error.isNotBlank() && error != "null" -> "(☓‿‿☓)"
            visible >= 20 -> "(°▃▃°)"
            visible > 0 -> "( ⚆⚆)"
            scan > 0 -> "(-__-)"
            else -> "(≖‿‿≖)"
        }
        val message = when {
            error.isNotBlank() && error != "null" -> "Something disturbs the bridge"
            visible >= 20 -> "Eyes on the Nine Realms"
            visible > 0 -> "Watching $visible nearby networks"
            scan > 0 -> "The bridge is quiet"
            else -> "Opening the Bifrost"
        }

        uiState = uiState.copy(
            connection = "CONNECTED",
            node = json.optString("node", "OVN-002"),
            codename = json.optString("codename", "Josh"),
            mode = mode,
            face = face,
            networks = visible,
            channel = list.firstOrNull()?.channel ?: "--",
            scanNumber = scan,
            networkList = list,
            message = message,
            raw = json.toString(2)
        )
    }

    override fun onDestroy() {
        try { socket?.close() } catch (_: Exception) {}
        io.shutdownNow()
        super.onDestroy()
    }
}

data class WifiNetwork(
    val ssid: String,
    val channel: String,
    val signal: Int,
    val security: String
)

data class JoshUiState(
    val connection: String = "DISCONNECTED",
    val node: String = "OVN-002",
    val codename: String = "JOSH",
    val mode: String = "--",
    val face: String = "(◕‿‿◕)",
    val networks: Int = 0,
    val clients: Int = 0,
    val captures: Int = 0,
    val channel: String = "--",
    val battery: String = "--",
    val temperature: String = "--",
    val scanNumber: Int = 0,
    val networkList: List<WifiNetwork> = emptyList(),
    val message: String = "Waiting for Josh…",
    val raw: String = ""
)

@Composable
private fun JoshScreen(
    state: JoshUiState,
    onConnect: () -> Unit,
    onRefresh: () -> Unit,
    onDoctor: () -> Unit,
    onCheckUpdate: () -> Unit
) {
    Scaffold { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(18.dp)
                .fillMaxSize()
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("${state.node} • ${state.codename.uppercase()}", fontSize = 26.sp, fontWeight = FontWeight.Bold)
            Text("HEIMDALL COMPANION", fontSize = 14.sp)
            Spacer(Modifier.height(8.dp))
            AssistChip(onClick = onConnect, label = { Text("BLUETOOTH: ${state.connection}") })

            Spacer(Modifier.height(20.dp))
            Text(state.face, fontSize = 44.sp, textAlign = TextAlign.Center)
            Text(state.message, fontSize = 16.sp, textAlign = TextAlign.Center)
            Text("MODE: ${state.mode}  •  SCAN #${state.scanNumber}", fontWeight = FontWeight.Bold)

            Spacer(Modifier.height(20.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                Metric("NET", state.networks.toString())
                Metric("CLI", state.clients.toString())
                Metric("CAP", state.captures.toString())
                Metric("CH", state.channel)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                Metric("BAT", state.battery)
                Metric("TEMP", state.temperature)
            }

            Spacer(Modifier.height(18.dp))
            Button(onClick = onRefresh, modifier = Modifier.fillMaxWidth()) { Text("REFRESH WIFI") }

            Spacer(Modifier.height(14.dp))
            HorizontalDivider()
            Spacer(Modifier.height(10.dp))
            Text("VISIBLE NETWORKS", fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth())
            if (state.networkList.isEmpty()) {
                Text("No passive inventory received yet", modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp))
            } else {
                state.networkList.take(30).forEach { network ->
                    NetworkRow(network)
                    HorizontalDivider()
                }
            }

            Spacer(Modifier.height(18.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onDoctor, modifier = Modifier.weight(1f)) { Text("DOCTOR") }
                OutlinedButton(onClick = onCheckUpdate, modifier = Modifier.weight(1f)) { Text("CHECK UPDATE") }
            }

            Spacer(Modifier.height(18.dp))
            Text("Protocol debug", fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth())
            Text(state.raw.ifBlank { "No data yet" }, fontSize = 10.sp, modifier = Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun Metric(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Text(label, fontSize = 11.sp)
    }
}

@Composable
private fun NetworkRow(network: WifiNetwork) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(Modifier.weight(1f)) {
            Text(network.ssid.ifBlank { "(hidden)" }, fontWeight = FontWeight.SemiBold)
            Text(network.security, fontSize = 11.sp)
        }
        Text("CH ${network.channel}", modifier = Modifier.padding(horizontal = 10.dp))
        Text("${network.signal}%", fontWeight = FontWeight.Bold)
    }
}
