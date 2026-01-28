<script lang="ts">
  import { onMount } from 'svelte';

  let ready = false;

  onMount(() => {
    ready = true;
  });
</script>

<main>
  <header>
    <h1>YouTube Archive Browser</h1>
    <p class="subtitle">Browse your offline YouTube archive</p>
  </header>

  {#if ready}
    <div class="content">
      <p>Loading archive data...</p>
      <p class="hint">
        This is the annextube frontend placeholder.
        Components will be added in the next steps.
      </p>
    </div>
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu,
                 Cantarell, 'Helvetica Neue', sans-serif;
    background: #f5f5f5;
  }

  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
  }

  header {
    text-align: center;
    padding: 40px 20px;
    background: white;
    border-radius: 8px;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  h1 {
    margin: 0;
    color: #333;
    font-size: 2.5rem;
  }

  .subtitle {
    margin: 10px 0 0 0;
    color: #666;
    font-size: 1.1rem;
  }

  .content {
    background: white;
    padding: 40px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    text-align: center;
  }

  .hint {
    color: #999;
    font-size: 0.9rem;
    margin-top: 20px;
  }
</style>
