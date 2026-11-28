plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.chaquo.python")
}

// Version comes from the git tag in CI: PSEEK_VERSION=v1.2.3 -> versionCode 10203.
val pseekVersion = System.getenv("PSEEK_VERSION") ?: ""
val versionMatch = Regex("""^v?(\d+)\.(\d+)\.(\d+)(.*)$""").find(pseekVersion)
val versionCode = versionMatch?.destructured?.let { (a, b, c, _) -> a.toInt() * 10000 + b.toInt() * 100 + c.toInt() } ?: 1
val versionName = versionMatch?.let { pseekVersion.removePrefix("v") } ?: "0.0.0-dev"

// Chaquopy: the PSEEK core is stdlib-only, so no pip packages are needed.
// (The GUI is PySide6 and is deliberately not shipped; Kotlin Compose replaces it.)
chaquopy {
    defaultConfig {
        version = "3.11"
    }
}

val keystorePath: String? = System.getenv("ANDROID_KEYSTORE_PATH")?.takeIf { it.isNotBlank() }

android {
    namespace = "ca.andrej_zeravatech.pseekapk"
    compileSdk = 35

    defaultConfig {
        applicationId = "ca.andrej_zeravatech.pseekapk"
        minSdk = 26
        targetSdk = 35
        versionCode = versionCode
        versionName = versionName
        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (keystorePath != null) {
            create("release") {
                storeFile = file(keystorePath)
                storeType = "pkcs12"
                storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("ANDROID_KEY_ALIAS")
                keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (keystorePath != null) signingConfig = signingConfigs.getByName("release")
        }
        debug {
            applicationIdSuffix = ".test"
            versionNameSuffix = "-test"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
    lint {
        checkReleaseBuilds = true
        abortOnError = true
        disable += listOf("MissingTranslation")
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-core")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.work:work-runtime-ktx:2.10.0")
}
