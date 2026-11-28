package ca.andrej_zeravatech.pseekapk.work

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import ca.andrej_zeravatech.pseekapk.Bridge
import ca.andrej_zeravatech.pseekapk.R
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Phase A6: periodic search in the background, with a local notification. */
class SearchWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            Bridge.init(applicationContext)
            val init = Bridge.initialize()
            if (!init.optBoolean("ok", false)) return@withContext Result.retry()
            val location = inputData.getString("location") ?: "toronto_remote"
            val result = Bridge.call("search", location, 20)
            val count = result.optInt("count", 0)
            notify(count)
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }

    private fun notify(count: Int) {
        val manager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL, applicationContext.getString(R.string.channel_jobs),
                NotificationManager.IMPORTANCE_DEFAULT,
            ).apply { description = applicationContext.getString(R.string.channel_description) }
            manager.createNotificationChannel(channel)
        }
        val n = NotificationCompat.Builder(applicationContext, CHANNEL)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("PSEEK")
            .setContentText(if (count > 0) "$count novih poslova — prijave čekaju odobrenje" else "Pretraga završena, novih poslova nema")
            .setAutoCancel(true)
            .build()
        manager.notify(NOTIFICATION_ID, n)
    }

    companion object {
        const val CHANNEL = "pseek_jobs"
        const val NOTIFICATION_ID = 42
    }
}
