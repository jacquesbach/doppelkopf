<script>
  import { nav } from "./lib/nav.svelte.js";
  import Landing from "./pages/Landing.svelte";
  import CreateTable from "./pages/CreateTable.svelte";
  import JoinTable from "./pages/JoinTable.svelte";
  import TablePage from "./pages/TablePage.svelte";
  import Legal from "./pages/Legal.svelte";
  import Admin from "./pages/Admin.svelte";
  import NotFound from "./pages/NotFound.svelte";
  import Rules from "./pages/Rules.svelte";
  import SiteBanner from "./components/ui/SiteBanner.svelte";
  import FriendsHost from "./components/community/FriendsHost.svelte";
  import { api } from "./lib/services.js";
  import { siteSettings } from "./lib/siteSettings.svelte.js";
  import { presence } from "./lib/presence.svelte.js";
  import { onMount } from "svelte";
  import { applySeo } from "./lib/seo.js";
  import { SITE_URL } from "./lib/site.js";

  const route = $derived(nav.route);

  // Design-Einstellungen und Banner des Betreibers laden (ohne Antwort gelten die Standardwerte).
  onMount(async () => {
    await siteSettings.load(api);
    presence.sync(); // Online-Status nur verbinden, wenn eingeschaltet und vom Betreiber erlaubt
  });

  // Titel, Beschreibung, robots und kanonische Adresse folgen jedem Seitenwechsel (Single-Page-App).
  $effect(() => {
    applySeo({ name: route.name, page: route.page }, SITE_URL);
  });
</script>

<SiteBanner />
{#if route.name === "landing"}
  <Landing />
{:else if route.name === "create"}
  <CreateTable />
{:else if route.name === "join"}
  {#key route.code}<JoinTable code={route.code} />{/key}
{:else if route.name === "table"}
  {#key route.code}<TablePage code={route.code} />{/key}
{:else if route.name === "legal"}
  <Legal page={route.page} />
{:else if route.name === "rules"}
  <Rules />
{:else if route.name === "admin"}
  <Admin />
{:else}
  <NotFound />
{/if}

{#if route.name !== "admin"}<FriendsHost />{/if}
