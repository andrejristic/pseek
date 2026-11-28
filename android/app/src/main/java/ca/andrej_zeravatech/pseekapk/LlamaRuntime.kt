package ca.andrej_zeravatech.pseekapk

import android.app.ActivityManager
import android.content.Context
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

/**
 * Phase L: on-device GGUF via llama.cpp.
 *
 * The llama-server executable and its shared libraries are fetched into
 * app/src/main/jniLibs/arm64-v8a by android/scripts/fetch-llama.sh in CI and are
 * therefore installed into nativeLibraryDir as executable files. Python never
 * loads a native module: it talks OpenAI-compatible HTTP to 127.0.0.1:8765.
 */
object LlamaRuntime {
    private const val PORT = 8765
    private const val LIB = "libllama_server.so"
    private var process: Process? = null
    private var modelPath: String? = null

    data class Model(val id: String, val label: String, val file: String, val url: String,
                     val sizeGb: Double, val minRamGb: Int)

    val MODELS = listOf(
        Model("qwen05", "Qwen2.5 0.5B (mali, brzi)", "qwen2.5-0.5b-instruct-q4_k_m.gguf",
            "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
            0.4, 3),
        Model("qwen15", "Qwen2.5 1.5B (preporuka)", "qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
            1.1, 4),
        Model("qwen3", "Qwen2.5 3B (jači, sporiji)", "qwen2.5-3b-instruct-q4_k_m.gguf",
            "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
            2.0, 8),
    )

    fun deviceInfo(context: Context): JSONObject {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val mem = ActivityManager.MemoryInfo().also { am.getMemoryInfo(it) }
        return JSONObject()
            .put("totalRamGb", round1(mem.totalMem / (1024.0 * 1024 * 1024)))
            .put("freeRamGb", round1(mem.availMem / (1024.0 * 1024 * 1024)))
            .put("cores", Runtime.getRuntime().availableProcessors())
            .put("abis", JSONArray(Build.SUPPORTED_ABIS.toList()))
            .put("sdk", Build.VERSION.SDK_INT)
            .put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
            .put("arm64", Build.SUPPORTED_ABIS.contains("arm64-v8a"))
    }

    private fun round1(v: Double) = Math.round(v * 10) / 10.0

    fun recommend(info: JSONObject): JSONObject {
        val ram = info.optDouble("totalRamGb", 4.0)
        val arm64 = info.optBoolean("arm64", false)
        val pick = MODELS.lastOrNull { ram >= it.minRamGb } ?: MODELS.first()
        val out = JSONArray()
        for (m in MODELS) {
            out.put(JSONObject()
                .put("id", m.id).put("label", m.label).put("file", m.file).put("url", m.url)
                .put("sizeGb", m.sizeGb).put("minRamGb", m.minRamGb)
                .put("fits", arm64 && ram >= m.minRamGb))
        }
        return JSONObject().put("recommended", pick.id).put("models", out)
            .put("supported", arm64)
    }

    fun modelsDir(context: Context): File {
        val dir = File(context.getExternalFilesDir("models"), "gguf")
        dir.mkdirs()
        return dir
    }

    fun modelFiles(context: Context): JSONArray {
        val out = JSONArray()
        modelsDir(context).listFiles { f -> f.isFile && f.name.endsWith(".gguf") }
            ?.sortedBy { it.name }?.forEach { out.put(it.name) }
        return out
    }

    fun status(): JSONObject = JSONObject()
        .put("running", process?.isAlive == true && alive())
        .put("model", modelPath)
        .put("port", PORT)

    private fun alive(): Boolean = try {
        val c = URL("http://127.0.0.1:$PORT/health").openConnection() as HttpURLConnection
        c.connectTimeout = 1000
        c.readTimeout = 1000
        c.use { responseCode == 200 }
    } catch (_: Exception) {
        false
    }

    fun start(context: Context, modelName: String): JSONObject {
        stop()
        val exe = File(context.applicationInfo.nativeLibraryDir, LIB)
        if (!exe.exists()) {
            return JSONObject().put("ok", false)
                .put("error", "llama.cpp nije u APK-u (CI nije preuzeo arm64 binarnu verziju)")
        }
        val model = File(modelsDir(context), modelName)
        if (!model.exists()) {
            return JSONObject().put("ok", false).put("error", "model nije preuzet: $modelName")
        }
        return try {
            val libDir = context.applicationInfo.nativeLibraryDir
            val pb = ProcessBuilder(
                exe.absolutePath,
                "-m", model.absolutePath,
                "--host", "127.0.0.1",
                "--port", PORT.toString(),
                "-c", "2048",
                "--n-gpu-layers", "0",
            )
            pb.redirectErrorStream(true)
            pb.environment()["LD_LIBRARY_PATH"] = libDir
            process = pb.start()
            modelPath = model.absolutePath
            var ready = false
            repeat(30) {
                if (alive()) { ready = true; return@repeat }
                Thread.sleep(1000)
            }
            if (!ready) {
                stop()
                JSONObject().put("ok", false).put("error", "llama-server se nije pokrenuo za 30 s")
            } else {
                JSONObject().put("ok", true).put("model", model.absolutePath).put("port", PORT)
            }
        } catch (e: Exception) {
            JSONObject().put("ok", false).put("error", e.toString())
        }
    }

    fun stop() {
        process?.destroy()
        try { process?.waitFor(3, TimeUnit.SECONDS) } catch (_: InterruptedException) { }
        process = null
        modelPath = null
    }
}
