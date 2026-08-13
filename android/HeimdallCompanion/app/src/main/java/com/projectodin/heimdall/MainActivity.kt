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
                    onRefresh = { send("status") },
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
                        message = "Bluetooth link established",
                        raw = hello
                    )
                }
                send("status")
            } catch (e: Exception) {
                runOnUiThread {
                    uiState = uiState.copy(
                        connection = "DISCONNECTED",
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
        if (cmd == "status" && json.optBoolean("ok")) {
            val radio = json.optJSONObject("radio")
            val currentMode = radio?.optString("mode", "--") ?: "--"
            val surveyAvailable = radio?.optBoolean("survey_available", false) ?: false
            val reason = radio?.optString("survey_unavailable_reason", "") ?: ""
            uiState = uiState.copy(
                node = json.optString("node", "OVN-002"),
                codename = json.optString("codename", "Josh"),
                mode = currentMode.uppercase(),
                surveyAvailable = surveyAvailable,
                message = if (surveyAvailable) "Watching the Bifrost" else (reason.ifBlank { "Watching the Bifrost" }),
                raw = json.toString(2)
            )
        } else {
            uiState = uiState.copy(
                message = json.optString("output", if (json.optBoolean("ok")) "Command completed" else "Command failed"),
                raw = json.toString(2)
            )
        }
    }

    override fun onDestroy() {
        try { socket?.close() } catch (_: Exception) {}
        io.shutdownNow()
        super.onDestroy()
    }
}

data class JoshUiState(
    val connection: String = "DISCONNECTED",
    val node: String = "OVN-002",
    val codename: String = "JOSH",
    val mode: String = "--",
    val surveyAvailable: Boolean = false,
    val face: String = "(◕‿‿◕)",
    val networks: Int = 0,
    val clients: Int = 0,
    val captures: Int = 0,
    val channel: String = "--",
    val battery: String = "--",
    val temperature: String = "--",
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
            Text("OVN-002 • JOSH", fontSize = 26.sp, fontWeight = FontWeight.Bold)
            Text("HEIMDALL COMPANION", fontSize = 14.sp)
            Spacer(Modifier.height(8.dp))
            AssistChip(
                onClick = onConnect,
                label = { Text("BLUETOOTH: ${state.connection}") }
            )

            Spacer(Modifier.height(24.dp))
            Text(state.face, fontSize = 44.sp, textAlign = TextAlign.Center)
            Text(state.message, fontSize = 16.sp, textAlign = TextAlign.Center)
            Text("MODE: ${state.mode}", fontWeight = FontWeight.Bold)

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

            Spacer(Modifier.height(20.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onRefresh, modifier = Modifier.weight(1f)) { Text("REFRESH") }
                Button(onClick = onDoctor, modifier = Modifier.weight(1f)) { Text("DOCTOR") }
            }
            Button(onClick = onCheckUpdate, modifier = Modifier.fillMaxWidth()) { Text("CHECK UPDATE") }

            Spacer(Modifier.height(18.dp))
            HorizontalDivider()
            Spacer(Modifier.height(10.dp))
            Text("Bluetooth protocol response", fontWeight = FontWeight.Bold)
            Text(state.raw.ifBlank { "No data yet" }, fontSize = 12.sp)
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
