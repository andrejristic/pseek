package ca.andrej_zeravatech.pseekapk

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.ViewModelProvider
import ca.andrej_zeravatech.pseekapk.ui.PseekApp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val vm = ViewModelProvider(this)[MainViewModel::class.java]
        setContent { PseekApp(vm) }
    }
}
