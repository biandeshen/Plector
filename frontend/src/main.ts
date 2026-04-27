import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

import 'highlight.js/styles/github-dark.css'
import './styles/variables.css'
import './styles/base.css'
import './styles/animations.css'
import './styles/markdown.css'

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
