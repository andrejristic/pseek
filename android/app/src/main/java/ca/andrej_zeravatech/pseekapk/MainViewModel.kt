package ca.andrej_zeravatech.pseekapk

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import ca.andrej_zeravatech.pseekapk.work.SearchWorker
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.WorkManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

data class ChatLine(val mine: Boolean, val text: String)

class MainViewModel : ViewModel() {
    private val _status = MutableStateFlow(JSONObject())
    val status: StateFlow<JSONObject> = _status
    private val _jobs = MutableStateFlow(JSONArray())
    val jobs: StateFlow<JSONArray> = _jobs
    private val _documents = MutableStateFlow(JSONArray())
    val documents: StateFlow<JSONArray> = _documents
    private val _applications = MutableStateFlow(JSONArray())
    val applications: StateFlow<JSONArray> = _applications
    private val _chat = MutableStateFlow<List<ChatLine>>(emptyList())
    val chat: StateFlow<List<ChatLine>> = _chat
    private val _proposal = MutableStateFlow(JSONObject())
    val proposal: StateFlow<JSONObject> = _proposal
    private val _error = MutableStateFlow("")
    val error: StateFlow<String> = _error
    private val _busy = MutableStateFlow(false)
    val busy: StateFlow<Boolean> = _busy
    private val _notice = MutableStateFlow("")
    val notice: StateFlow<String> = _notice
    private val _device = MutableStateFlow(JSONObject())
    val device: StateFlow<JSONObject> = _device
    private val _models = MutableStateFlow(JSONArray())
    val models: StateFlow<JSONArray> = _models
    private val _llama = MutableStateFlow(JSONObject())
    val llama: StateFlow<JSONObject> = _llama

    fun init(context: Context) {
        Bridge.init(context)
        _device.value = LlamaRuntime.deviceInfo(context)
        _models.value = LlamaRuntime.recommend(_device.value).optJSONArray("models") ?: JSONArray()
        _llama.value = LlamaRuntime.status()
        run {
            val r = Bridge.initialize()
            if (!r.optBoolean("ok", false)) _error.value = r.optString("error", "Greška pri pokretanju")
            refresh()
        }
    }

    private inline fun run(crossinline block: () -> Unit) {
        viewModelScope.launch {
            _busy.value = true
            try { withContext(Dispatchers.IO) { block() } }
            catch (e: Exception) { _error.value = e.message ?: e.toString() }
            finally { _busy.value = false }
        }
    }

    private fun check(r: JSONObject): Boolean {
        if (!r.optBoolean("ok", false)) {
            _error.value = r.optString("error", "Neočekivana greška")
            return false
        }
        _error.value = ""
        return true
    }

    fun refresh() = run {
        val s = Bridge.call("status")
        if (check(s)) _status.value = s
        val j = Bridge.call("jobs")
        if (j.optBoolean("ok")) _jobs.value = j.optJSONArray("jobs") ?: JSONArray()
        val d = Bridge.call("documents")
        if (d.optBoolean("ok")) _documents.value = d.optJSONArray("files") ?: JSONArray()
        val a = Bridge.call("applications")
        if (a.optBoolean("ok")) _applications.value = a.optJSONArray("applications") ?: JSONArray()
    }

    fun search(location: String) = run {
        val r = Bridge.call("search", location, 30)
        if (check(r)) {
            _jobs.value = r.optJSONArray("jobs") ?: JSONArray()
            _notice.value = "Pronađeno ${r.optInt("count", 0)} poslova"
        }
    }

    fun import(context: Context, uri: Uri) = run {
        val name = displayName(context, uri) ?: "document.txt"
        val tmp = File(context.cacheDir, name)
        context.contentResolver.openInputStream(uri)?.use { input ->
            tmp.outputStream().use { out -> input.copyTo(out) }
        } ?: throw Exception("Ne mogu da pročitam fajl")
        val r = Bridge.call("add_document", tmp.absolutePath, name)
        if (check(r)) {
            _notice.value = "Dokument dodat: $name"
            refresh()
        }
    }

    private fun displayName(context: Context, uri: Uri): String? {
        context.contentResolver.query(uri, null, null, null, null)?.use { c ->
            val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0 && c.moveToFirst()) return c.getString(idx)
        }
        return null
    }

    fun sendChat(text: String) = run {
        if (text.isBlank()) return@run
        _chat.value = _chat.value + ChatLine(true, text)
        val r = Bridge.call("chat", text)
        if (check(r)) _chat.value = _chat.value + ChatLine(false, r.optString("text", ""))
    }

    fun prepare(index: Int) = run {
        val r = Bridge.call("prepare", index)
        if (check(r)) _proposal.value = r else _proposal.value = JSONObject()
    }

    fun decide(approved: Boolean) = run {
        val pid = _proposal.value.optString("id", "")
        if (pid.isEmpty()) return@run
        val r = Bridge.call("apply_proposal", pid, approved)
        if (check(r)) {
            _proposal.value = JSONObject()
            _notice.value = if (approved) "Prijava je odobrena i poslata" else "Prijava je odbijena"
            refresh()
        }
    }

    fun setBackend(url: String) = run {
        val r = Bridge.call("set_backend", url)
        if (check(r)) {
            Bridge.backendUrl = url.trim()
            refresh()
        }
    }

    fun testBackend() = run {
        val r = Bridge.call("test_backend")
        _notice.value = if (r.optBoolean("connected", false)) "Backend povezan" else "Backend nije dostupan (test režim)"
        check(r)
    }

    fun connectEmail(address: String, password: String) = run {
        val r = Bridge.call("connect_email", address, password, "", "")
        if (check(r)) { _notice.value = "Email povezan"; refresh() }
    }

    fun setKey(provider: String, key: String) = run {
        val r = Bridge.call("set_llm_key", provider, key)
        if (check(r)) { _notice.value = "Ključ sačuvan u trezoru"; refresh() }
    }

    fun checkout(tier: String, approved: Boolean) = run {
        val r = Bridge.call("checkout", tier, "monthly", approved)
        if (check(r)) _notice.value = r.optJSONObject("result")?.optString("note")
            ?: r.optJSONObject("result")?.optString("status") ?: "Zahtev poslat"
    }

    fun restoreStart(email: String) = run {
        val r = Bridge.call("restore_start", email)
        if (check(r)) _notice.value = "Kod je poslat na $email"
    }

    fun restoreVerify(code: String) = run {
        val r = Bridge.call("restore_verify", code)
        if (check(r)) { _notice.value = "Pretplata povezana sa ovim uređajem"; refresh() }
    }

    fun startModel(context: Context, file: String) = run {
        val r = LlamaRuntime.start(context, file)
        if (check(r)) {
            val use = Bridge.call("use_local_model", r.optString("model"))
            if (check(use)) refresh()
        }
        _llama.value = LlamaRuntime.status()
    }

    fun stopModel() = run {
        LlamaRuntime.stop()
        Bridge.call("stop_local_model")
        _llama.value = LlamaRuntime.status()
        refresh()
    }

    fun toggleBackground(context: Context, enabled: Boolean) {
        Bridge.backgroundSearch = enabled
        if (enabled) {
            val req = PeriodicWorkRequestBuilder<SearchWorker>(6, TimeUnit.HOURS)
                .addTag("pseek-search").build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                "pseek-search", ExistingPeriodicWorkPolicy.UPDATE, req)
        } else {
            WorkManager.getInstance(context).cancelUniqueWork("pseek-search")
        }
    }

    fun clearError() { _error.value = "" }
    fun clearNotice() { _notice.value = "" }
}
