package com.projectodin.heimdall

import android.Manifest
import android.app.Activity
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.UUID
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val io = Executors.newSingleThreadExecutor()
    private val sppUuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
    private var socket: BluetoothSocket? = null
    private var reader: BufferedReader? = null

    private lateinit var connection: TextView
    private lateinit var node: TextView
    private lateinit var mode: TextView
    private lateinit var survey: Button
    private lateinit var detail: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(buildUi())
        if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.BLUETOOTH_SCAN), 100)
        } else connectHeimdall()
    }

    private fun buildUi(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(36, 44, 36, 36)
            setBackgroundColor(Color.rgb(5, 15, 30))
        }
        fun text(value: String, size: Float = 18f) = TextView(this).apply {
            text = value; textSize = size; setTextColor(Color.WHITE); setPadding(0, 10, 0, 10)
        }
        root.addView(text("PROJECT ODIN", 28f))
        root.addView(text("HEIMDALL COMPANION", 20f))
        connection = text("Bluetooth: DISCONNECTED", 16f); root.addView(connection)
        node = text("Josh / OVN-002", 24f); root.addView(node)
        mode = text("Mode: --", 20f); root.addView(mode)

        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER }
        val connect = Button(this).apply { text = "CONNECT"; setOnClickListener { connectHeimdall() } }
        val refresh = Button(this).apply { text = "REFRESH"; setOnClickListener { send("status") } }
        actions.addView(connect); actions.addView(refresh); root.addView(actions)

        val modes = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER }
        val connected = Button(this).apply { text = "CONNECTED"; isEnabled = false }
        survey = Button(this).apply { text = "SURVEY"; isEnabled = false }
        val recovery = Button(this).apply { text = "RECOVERY"; isEnabled = false }
        modes.addView(connected); modes.addView(survey); modes.addView(recovery); root.addView(modes)

        val tools = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER }
        tools.addView(Button(this).apply { text = "DOCTOR"; setOnClickListener { send("doctor") } })
        tools.addView(Button(this).apply { text = "CHECK UPDATE"; setOnClickListener { send("check-update") } })
        root.addView(tools)

        detail = text("Waiting for HEIMDALL…", 15f); detail.setTextColor(Color.rgb(110, 210, 255))
        val scroll = ScrollView(this).apply { addView(detail) }
        root.addView(scroll, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
        return root
    }

    @Suppress("MissingPermission")
    private fun connectHeimdall() {
        if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) return
        connection.text = "Bluetooth: CONNECTING…"
        io.execute {
            try {
                socket?.close()
                val manager = getSystemService(BluetoothManager::class.java)
                val adapter: BluetoothAdapter = manager.adapter ?: error("Bluetooth unavailable")
                val device: BluetoothDevice = adapter.bondedDevices.firstOrNull { it.name.equals("HEIMDALL", true) }
                    ?: error("Pair HEIMDALL in Android Bluetooth settings first")
                adapter.cancelDiscovery()
                val s = device.createRfcommSocketToServiceRecord(sppUuid)
                s.connect()
                socket = s
                reader = BufferedReader(InputStreamReader(s.inputStream))
                val hello = reader!!.readLine()
                runOnUiThread {
                    connection.text = "Bluetooth: CONNECTED"
                    detail.text = hello
                }
                send("status")
            } catch (e: Exception) {
                runOnUiThread { connection.text = "Bluetooth: DISCONNECTED"; detail.text = e.message ?: e.toString() }
            }
        }
    }

    private fun send(cmd: String) {
        io.execute {
            try {
                val s = socket ?: error("Not connected")
                val request = JSONObject().put("cmd", cmd).toString() + "\n"
                s.outputStream.write(request.toByteArray())
                s.outputStream.flush()
                val response = reader?.readLine() ?: error("No response from HEIMDALL")
                val json = JSONObject(response)
                runOnUiThread { render(cmd, json) }
            } catch (e: Exception) {
                runOnUiThread { detail.text = e.message ?: e.toString() }
            }
        }
    }

    private fun render(cmd: String, json: JSONObject) {
        if (cmd == "status" && json.optBoolean("ok")) {
            node.text = "${json.optString("codename", "Josh")} / ${json.optString("node", "OVN-002")}"
            val radio = json.optJSONObject("radio")
            val currentMode = radio?.optString("mode", "--") ?: "--"
            mode.text = "Mode: ${currentMode.uppercase()}"
            val available = radio?.optBoolean("survey_available", false) ?: false
            survey.isEnabled = available
            survey.text = if (available) "SURVEY" else "SURVEY\nSECOND RADIO REQUIRED"
            val reason = radio?.optString("survey_unavailable_reason", "") ?: ""
            detail.text = buildString {
                append("Bluetooth control: ONLINE\n")
                append("Management radio: ${radio?.optString("management_interface", "--")}\n")
                append("Interfaces: ${radio?.optJSONArray("interfaces_present") ?: "[]"}\n")
                append("Survey available: $available\n")
                if (reason.isNotBlank()) append("$reason\n")
                append("\nRecovery portal: ${json.optJSONObject("recovery")?.optString("portal", "--")}")
            }
        } else {
            detail.text = json.optString("output", json.toString(2))
        }
    }

    override fun onDestroy() {
        try { socket?.close() } catch (_: Exception) {}
        io.shutdownNow()
        super.onDestroy()
    }
}
