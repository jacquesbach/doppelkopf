<script>
  import { nav } from "./lib/nav.svelte.js";
  import Landing from "./pages/Landing.svelte";
  import CreateTable from "./pages/CreateTable.svelte";
  import JoinTable from "./pages/JoinTable.svelte";
  import TablePage from "./pages/TablePage.svelte";
  import Legal from "./pages/Legal.svelte";
  import Admin from "./pages/Admin.svelte";
  import NotFound from "./pages/NotFound.svelte";

  const route = $derived(nav.route);
</script>

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
{:else if route.name === "admin"}
  <Admin />
{:else}
  <NotFound />
{/if}
