package ca.andrej_zeravatech.pseekapk

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.chaquo.python.Python
import org.json.JSONObject
import java.security.KeyStore
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.KeyGenerator

/**
 * Single entry point to the PSEEK Python core.
 *
 * Every method returns a JSONObject with an "ok" flag; callers must check it.
 * The vault passphrase is generated once and protected by the Android Keystore,
 * so the user never types it (phase A3 of ANDROID-PLAN.md).
 */
object Bridge {
    private const val PREFS = "pseek_settings"
    private const val KEY_ALIAS = "pseek_workspace_key"
    private const val ANDROID_KEYSTORE = "AndroidKeyStore"

    private lateinit var context: Context
    private var moduleInitialized = false

    fun init(context: Context) {
        this.context = context.applicationContext
    }

    private fun prefs() = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var backendUrl: String
        get() = prefs().getString("backend_url", "") ?: ""
        set(value) = prefs().edit().putString("backend_url", value.trim()).apply()

    var language: String
        get() = prefs().getString("language", "sr") ?: "sr"
        set(value) = prefs().edit().putString("language", value).apply()

    var darkTheme: Boolean
        get() = prefs().getBoolean("dark", false)
        set(value) = prefs().edit().putBoolean("dark", value).apply()

    var backgroundSearch: Boolean
        get() = prefs().getBoolean("background", false)
        set(value) = prefs().edit().putBoolean("background", value).apply()

    private fun module() = Python.getInstance().getModule("mobile_api")

    /** Call a Python function and parse its JSON result. */
    fun call(name: String, vararg args: Any): JSONObject {
        val raw = module().callAttr(name, *args)?.toString() ?: return JSONObject().put("ok", false).put("error", "empty result")
        return try {
            JSONObject(raw)
        } catch (e: Exception) {
            JSONObject().put("ok", false).put("error", "bad JSON: $e")
        }
    }

    fun initialize(): JSONObject {
        val base = context.getExternalFilesDir("pseek")?.absolutePath
            ?: context.filesDir.absolutePath
        val result = call("init", base, passphrase(), backendUrl)
        moduleInitialized = result.optBoolean("ok", false)
        return result
    }

    fun ensure(): JSONObject = if (moduleInitialized) call("status") else initialize()

    // ------------------------------------------------------------ keystore
    private fun keyStore(): KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    private fun ensureKey() {
        if (keyStore().containsAlias(KEY_ALIAS)) return
        val spec = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()
        KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE).apply {
            init(spec)
            generateKey()
        }
    }

    private fun encrypt(plain: String): String {
        ensureKey()
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, keyStore().getKey(KEY_ALIAS, null))
        val iv = cipher.iv
        val data = cipher.doFinal(plain.toByteArray(Charsets.UTF_8))
        return Base64.encodeToString(iv + data, Base64.DEFAULT)
    }

    private fun decrypt(encoded: String): String {
        ensureKey()
        val all = Base64.decode(encoded, Base64.DEFAULT)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, keyStore().getKey(KEY_ALIAS, null), GCMParameterSpec(128, all.copyOfRange(0, 12)))
        return String(cipher.doFinal(all.copyOfRange(12, all.size)), Charsets.UTF_8)
    }

    private fun passphrase(): String {
        val stored = prefs().getString("vault_pass", null)
        if (!stored.isNullOrBlank()) return try { decrypt(stored) } catch (_: Exception) {
            newPassphrase().also { prefs().edit().putString("vault_pass", encrypt(it)).apply() }
        }
        val fresh = newPassphrase()
        prefs().edit().putString("vault_pass", encrypt(fresh)).apply()
        return fresh
    }

    private fun newPassphrase(): String {
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        return Base64.encodeToString(bytes, Base64.NO_WRAP or Base64.URL_SAFE)
    }
}
