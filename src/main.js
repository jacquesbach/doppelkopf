// Schriften lokal gebündelt (@fontsource): keine Anfragen an Google, funktioniert offline.
import "@fontsource/inter/400.css";
import "@fontsource/inter/600.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/space-mono/400.css";
import "@fontsource/space-mono/700.css";
import "./styles/global.css";

import { mount } from "svelte";
import App from "./App.svelte";

mount(App, { target: document.getElementById("app") });
