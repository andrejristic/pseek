package ca.andrej_zeravatech.pseekapk.ui

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import ca.andrej_zeravatech.pseekapk.Bridge
import ca.andrej_zeravatech.pseekapk.MainViewModel
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONArray
import org.json.JSONObject

private val TABS_SR = listOf("Poslovi", "Dokumenti", "Prijave", "Ćaskanje", "Podešavanja")
private val TABS_EN = listOf("Jobs", "Documents", "Applications", "Chat", "Settings")

@Composable
fun PseekApp(vm: MainViewModel) {
    val context = LocalContext.current
    val snackbar = remember { SnackbarHostState() }
    var dark by remember { mutableStateOf(Bridge.darkTheme) }
    val lang by remember { mutableStateOf(Bridge.language) }
    val tabs = if (lang == "sr") TABS_SR else TABS_EN
    var tab by remember { mutableStateOf(0) }
    val busy by vm.busy.collectLatestState(false)

    LaunchedEffect(Unit) { vm.init(context) }
    LaunchedEffect(Unit) {
        vm.error.collectLatest { if (it.isNotBlank()) snackbar.showSnackbar(it) }
    }
    LaunchedEffect(Unit) {
        vm.notice.collectLatest { if (it.isNotBlank()) snackbar.showSnackbar(it) }
    }

    MaterialTheme(colorScheme = if (dark) darkColorScheme() else lightColorScheme()) {
        Scaffold(
            snackbarHost = { SnackbarHost(snackbar) },
            bottomBar = {
                NavigationBar {
                    tabs.forEachIndexed { i, label ->
                        NavigationBarItem(
                            selected = tab == i,
                            onClick = { tab = i },
                            icon = { Text("•") },
                            label = { Text(label) },
                        )
                    }
                }
            },
        ) { pad ->
            Column(Modifier.fillMaxSize().padding(pad).padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("PSEEK", style = MaterialTheme.typography.headlineMedium)
                    Spacer(Modifier.weight(1f))
                    if (busy) CircularProgressIndicator(Modifier.height(24.dp))
                }
                Spacer(Modifier.height(8.dp))
                when (tab) {
                    0 -> JobsScreen(vm, lang)
                    1 -> DocumentsScreen(vm)
                    2 -> ApplicationsScreen(vm, lang)
                    3 -> ChatScreen(vm, lang)
                    else -> SettingsScreen(vm, lang, dark, { dark = it }, context)
                }
            }
        }
    }
}

// Small helper: collect a StateFlow with an initial value without extra imports.
@Composable
private fun <T> StateFlow<T>.collectLatestState(initial: T): androidx.compose.runtime.State<T> {
    val state = remember { mutableStateOf(initial) }
    LaunchedEffect(this) { collectLatest { state.value = it } }
    return state
}

@Composable
private fun JobsScreen(vm: MainViewModel, lang: String) {
    val jobs by vm.jobs.collectLatestState(JSONArray())
    val proposal by vm.proposal.collectLatestState(JSONObject())
    var location by remember { mutableStateOf("toronto_remote") }

    OutlinedTextField(
        value = location, onValueChange = { location = it },
        label = { Text(if (lang == "sr") "Lokacija / fokus" else "Location / focus") },
        modifier = Modifier.fillMaxWidth(), singleLine = true,
    )
    Button(onClick = { vm.search(location) }, Modifier.fillMaxWidth()) {
        Text(if (lang == "sr") "Nađi poslove" else "Find jobs")
    }
    Spacer(Modifier.height(8.dp))

    if (proposal.optString("id", "").isNotEmpty()) {
        Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
            Column(Modifier.padding(12.dp)) {
                Text("${if (lang == "sr") "Predlog prijave" else "Proposal"}: ${proposal.optString("title")} — ${proposal.optString("company")}")
                Text(proposal.optString("note"), style = MaterialTheme.typography.bodySmall)
                val lines = proposal.optJSONArray("lines") ?: JSONArray()
                for (i in 0 until lines.length()) {
                    Text("• ${lines.optString(i)}", style = MaterialTheme.typography.bodySmall)
                }
                Row {
                    Button(onClick = { vm.decide(true) }) { Text(if (lang == "sr") "Odobri i pošalji" else "Approve & send") }
                    Spacer(Modifier.padding(4.dp))
                    Button(onClick = { vm.decide(false) }) { Text(if (lang == "sr") "Odbij" else "Reject") }
                }
            }
        }
    }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        items(jobs.length()) { i ->
            val j = jobs.optJSONObject(i) ?: return@items
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("${j.optString("title")} — ${j.optString("company")}", style = MaterialTheme.typography.titleMedium)
                    Text("fit ${j.optDouble("fit", 0.0)} · ${j.optString("verdict")} · ${j.optString("location")}",
                        style = MaterialTheme.typography.bodySmall)
                    Text(j.optString("description").take(180), style = MaterialTheme.typography.bodySmall)
                    Button(onClick = { vm.prepare(j.optInt("index", i)) }) {
                        Text(if (lang == "sr") "Pripremi prijavu" else "Prepare application")
                    }
                }
            }
        }
    }
}

@Composable
private fun DocumentsScreen(vm: MainViewModel) {
    val context = LocalContext.current
    val files by vm.documents.collectLatestState(JSONArray())
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) vm.import(context, uri)
    }
    Button(onClick = { picker.launch("*/*") }, Modifier.fillMaxWidth()) {
        Text("Dodaj dokument (PDF / DOCX / TXT)")
    }
    Spacer(Modifier.height(8.dp))
    LazyColumn {
        items(files.length()) { i -> Text("• ${files.optString(i)}", Modifier.padding(4.dp)) }
    }
}

@Composable
private fun ApplicationsScreen(vm: MainViewModel, lang: String) {
    val apps by vm.applications.collectLatestState(JSONArray())
    if (apps.length() == 0) {
        Text(if (lang == "sr") "Još nema prijava." else "No applications yet.")
    }
    LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        items(apps.length()) { i ->
            val a = apps.optJSONObject(i) ?: return@items
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp)) {
                    Text("${a.optString("title")} — ${a.optString("company")}")
                    Text(a.optString("state"), style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@Composable
private fun ChatScreen(vm: MainViewModel, lang: String) {
    val lines by vm.chat.collectLatestState(emptyList())
    var text by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize()) {
        LazyColumn(Modifier.weight(1f)) {
            items(lines) { line ->
                Text(
                    if (line.mine) "Ja: ${line.text}" else "PSEEK: ${line.text}",
                    Modifier.padding(vertical = 4.dp),
                )
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(value = text, onValueChange = { text = it }, modifier = Modifier.weight(1f),
                label = { Text(if (lang == "sr") "Poruka" else "Message") })
            Button(onClick = { vm.sendChat(text); text = "" }) { Text("➤") }
        }
    }
}

@Composable
private fun SettingsScreen(
    vm: MainViewModel, lang: String, dark: Boolean, onDark: (Boolean) -> Unit,
    context: android.content.Context,
) {
    val status by vm.status.collectLatestState(JSONObject())
    val llama by vm.llama.collectLatestState(JSONObject())
    val modelFiles by remember { mutableStateOf(ca.andrej_zeravatech.pseekapk.LlamaRuntime.modelFiles(context)) }
    var url by remember { mutableStateOf(Bridge.backendUrl) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var key by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }
    var background by remember { mutableStateOf(Bridge.backgroundSearch) }

    val notif = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Text("Status: ${status.optString("tier")} · backend ${status.optString("backend", "test režim")}",
                style = MaterialTheme.typography.titleSmall)
        }
        item {
            OutlinedTextField(value = url, onValueChange = { url = it }, modifier = Modifier.fillMaxWidth(),
                label = { Text("Backend URL (opciono)") }, singleLine = true)
            Row {
                Button(onClick = { vm.setBackend(url) }) { Text("Sačuvaj") }
                Spacer(Modifier.padding(4.dp))
                Button(onClick = { vm.testBackend() }) { Text("Probaj") }
            }
        }
        item {
            OutlinedTextField(value = email, onValueChange = { email = it }, modifier = Modifier.fillMaxWidth(),
                label = { Text("Tvoj email za prijave") }, singleLine = true)
            OutlinedTextField(value = password, onValueChange = { password = it }, modifier = Modifier.fillMaxWidth(),
                label = { Text("App lozinka za email") }, singleLine = true)
            Button(onClick = { vm.connectEmail(email, password) }) { Text("Poveži email") }
        }
        item {
            OutlinedTextField(value = key, onValueChange = { key = it }, modifier = Modifier.fillMaxWidth(),
                label = { Text("Tvoj LLM ključ (groq / mistral / anthropic)") }, singleLine = true)
            Button(onClick = { vm.setKey("groq", key) }) { Text("Sačuvaj ključ u trezor") }
        }
        item {
            Text("Vrati kupovinu (kod sa emaila)", style = MaterialTheme.typography.titleSmall)
            OutlinedTextField(value = code, onValueChange = { code = it }, modifier = Modifier.fillMaxWidth(),
                label = { Text("Šestocifreni kod") }, singleLine = true)
            Button(onClick = { vm.restoreStart(email) }) { Text("Pošalji kod") }
            Spacer(Modifier.padding(4.dp))
            Button(onClick = { vm.restoreVerify(code) }) { Text("Potvrdi kod") }
        }
        item {
            Text("Lokalni model (faza L)", style = MaterialTheme.typography.titleSmall)
            val info = vm.device.value
            Text("RAM ${info.optDouble("totalRamGb", 0.0)} GB · ${info.optString("device")} · server ${if (llama.optBoolean("running")) "aktivan" else "neaktivan"}")
            for (i in 0 until modelFiles.length()) {
                val name = modelFiles.optString(i)
                Button(onClick = { vm.startModel(context, name) }, Modifier.fillMaxWidth()) { Text(" Pokreni $name") }
            }
            if (llama.optBoolean("running")) Button(onClick = { vm.stopModel() }) { Text("Zaustavi model") }
            Text("Preuzmi GGUF u PSEEK/models/gguf, pa pokreni ovde. Modeli se nikad ne šalju.",
                style = MaterialTheme.typography.bodySmall)
        }
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Tamna tema"); Spacer(Modifier.weight(1f))
                Switch(checked = dark, onCheckedChange = { onDark(it); Bridge.darkTheme = it })
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(if (lang == "sr") "Pretraga u pozadini (6 h)" else "Background search (6h)")
                Spacer(Modifier.weight(1f))
                Switch(checked = background, onCheckedChange = {
                    background = it
                    if (it && Build.VERSION.SDK_INT >= 33) notif.launch(Manifest.permission.POST_NOTIFICATIONS)
                    vm.toggleBackground(context, it)
                })
            }
            Row {
                Button(onClick = { Bridge.language = "sr"; (context as? android.app.Activity)?.recreate() }) { Text("SR") }
                Spacer(Modifier.padding(4.dp))
                Button(onClick = { Bridge.language = "en"; (context as? android.app.Activity)?.recreate() }) { Text("EN") }
            }
        }
    }
}
