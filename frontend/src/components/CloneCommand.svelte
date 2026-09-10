<script lang="ts">
  import { probeGitUrl } from '@/services/git-discovery';

  /** Archive root relative to the page (e.g. '..'); '' until discovered. */
  export let baseUrl: string;
  export let channelDir: string | null;
  export let videoFilePath: string | null;
  export let isMultiChannel: boolean;

  /** A repository the user can clone, with paths relative to that repository. */
  interface Target {
    label: string;
    url: string;
    /** Path of the current video inside this repository, if any */
    relPath: string | null;
    /** Whether that path crosses into a subdataset of this repository */
    videoInSubdataset: boolean;
  }

  let collectionUrl: string | null = null;
  let channelUrl: string | null = null;
  let expanded = false;
  let activeTab: 'datalad' | 'git' = 'datalad';
  let copiedKey: string | null = null;

  // Re-probe whenever the archive root or the selected channel changes.
  // baseUrl starts out empty (the archive root is discovered asynchronously)
  // and probeGitUrl rejects that, so nothing is probed until it is known.
  let lastProbeKey = '';
  let probeSeq = 0;
  $: probeKey = `${baseUrl}|${channelDir}|${isMultiChannel}`;
  $: if (probeKey !== lastProbeKey) {
    lastProbeKey = probeKey;
    probeGit(baseUrl, channelDir, isMultiChannel);
  }

  async function probeGit(base: string, channel: string | null, multi: boolean) {
    const seq = ++probeSeq;

    // Without a known archive root every path below would be
    // server-root-absolute and probe some unrelated repository
    if (!base) {
      collectionUrl = null;
      channelUrl = null;
      return;
    }

    // Never keep offering the channel we have navigated away from
    channelUrl = null;

    const [collection, chan] = await Promise.all([
      probeGitUrl(base),
      multi && channel ? probeGitUrl(`${base}/${channel}`) : Promise.resolve(null),
    ]);

    // Drop results of a probe superseded while it was in flight
    if (seq !== probeSeq) return;

    collectionUrl = collection;
    channelUrl = chan;
  }

  // Derive the directory name clone creates from a clone URL
  // e.g. "https://example.com/archive/.git" → "archive"
  function dirnameOf(url: string): string {
    return decodeURIComponent(url.replace(/\/\.git\/?$/, '').split('/').pop() || 'repo');
  }

  // Quote only what a shell would otherwise mangle, so the common case stays
  // readable: archive directories can carry spaces once published by hand
  function shellArg(value: string): string {
    return /^[A-Za-z0-9._@%+:,\/-]+$/.test(value) ? value : `'${value.replace(/'/g, `'\\''`)}'`;
  }

  $: targets = buildTargets(collectionUrl, channelUrl, channelDir, videoFilePath, isMultiChannel);

  function buildTargets(
    collection: string | null,
    channel: string | null,
    dir: string | null,
    filePath: string | null,
    multi: boolean
  ): Target[] {
    const out: Target[] = [];

    // The channel's own dataset: the video lives directly in it
    if (channel) {
      out.push({
        label: 'This channel',
        url: channel,
        relPath: filePath ? `videos/${filePath}/` : null,
        videoInSubdataset: false,
      });
    }

    // The whole collection (superdataset), unless it is the same repository
    if (collection && collection !== channel) {
      // In a collection the video sits in a channel subdataset. Without a
      // channel in context (the plain #/video/{id} route) we cannot say which,
      // so offer the clone alone rather than a path that does not exist.
      const relPath = !filePath || (multi && !dir)
        ? null
        : `${multi ? `${dir}/` : ''}videos/${filePath}/`;

      out.push({
        label: 'Whole collection',
        url: collection,
        relPath,
        videoInSubdataset: multi,
      });
    }

    return out;
  }

  // Only worth labelling the groups when there is more than one of them
  $: showLabels = targets.length > 1;

  function buildCommands(tab: 'datalad' | 'git', target: Target): string[] {
    const dir = shellArg(dirnameOf(target.url));
    const relPath = target.relPath ? shellArg(target.relPath) : null;
    const cmds: string[] = [];

    if (tab === 'datalad') {
      cmds.push(`datalad clone ${target.url}`);
      if (relPath) {
        // datalad get installs the subdataset on the way, if any
        cmds.push(`cd ${dir} && datalad get ${relPath}`);
      }
    } else {
      cmds.push(`git clone ${target.url}`);
      // Only when the video lives in this very repository. Reaching into a
      // subdataset takes `git submodule update`, which resolves .gitmodules'
      // relative URLs against the clone URL — and those 404 for a clone URL
      // ending in /.git. The channel's own clone command above covers it.
      if (relPath && !target.videoInSubdataset) {
        cmds.push(`cd ${dir} && git annex get ${relPath}`);
      }
    }

    return cmds;
  }

  async function copyToClipboard(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
      copiedKey = key;
      setTimeout(() => {
        copiedKey = null;
      }, 1500);
    } catch {
      // Fallback: select text (clipboard API may not be available on file://)
    }
  }
</script>

{#if targets.length > 0}
  <div class="clone-section">
    <button
      class="clone-toggle"
      on:click={() => (expanded = !expanded)}
      aria-expanded={expanded}
      aria-controls="clone-panel"
    >
      <span class="toggle-icon">{expanded ? '\u25BC' : '\u25B6'}</span>
      Clone
    </button>

    {#if expanded}
      <div id="clone-panel" class="clone-panel" role="region" aria-label="Clone commands">
        <div class="tab-bar" role="tablist">
          <button
            class="tab"
            class:active={activeTab === 'datalad'}
            on:click={() => (activeTab = 'datalad')}
            role="tab"
            aria-selected={activeTab === 'datalad'}
            title="git clone works too for the clone step"
          >
            DataLad
          </button>
          <button
            class="tab"
            class:active={activeTab === 'git'}
            on:click={() => (activeTab = 'git')}
            role="tab"
            aria-selected={activeTab === 'git'}
          >
            Git / git-annex
          </button>
        </div>

        {#each targets as target (target.url)}
          <div class="commands">
            {#if showLabels}
              <div class="target-label">{target.label}</div>
            {/if}
            {#each buildCommands(activeTab, target) as cmd, i}
              <div class="command-line">
                <code class="command-text">$ {cmd}</code>
                <button
                  class="copy-btn"
                  on:click={() => copyToClipboard(cmd, `${target.url}|${i}`)}
                  title="Copy to clipboard"
                  aria-label="Copy to clipboard: {cmd}"
                >
                  {#if copiedKey === `${target.url}|${i}`}
                    <span class="copied-feedback">Copied!</span>
                  {:else}
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                  {/if}
                </button>
              </div>
            {/each}
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .clone-section {
    margin-left: auto;
  }

  .clone-toggle {
    background: none;
    border: none;
    color: #065fd4;
    font-size: 13px;
    cursor: pointer;
    padding: 4px 0;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }

  .clone-toggle:hover {
    text-decoration: underline;
  }

  .toggle-icon {
    font-size: 10px;
    width: 12px;
    display: inline-block;
  }

  .clone-panel {
    position: absolute;
    right: 0;
    top: 100%;
    margin-top: 4px;
    background: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    overflow: hidden;
    min-width: 420px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    z-index: 200;
  }

  .tab-bar {
    display: flex;
    border-bottom: 1px solid #e0e0e0;
    background: #fafafa;
  }

  .tab {
    background: none;
    border: none;
    padding: 8px 16px;
    font-size: 13px;
    cursor: pointer;
    color: #606060;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
  }

  .tab:hover {
    color: #030303;
  }

  .tab.active {
    color: #065fd4;
    border-bottom-color: #065fd4;
  }

  .commands {
    padding: 12px 16px;
  }

  .commands + .commands {
    border-top: 1px solid #e0e0e0;
  }

  .target-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #606060;
    padding-bottom: 4px;
  }

  .command-line {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 6px 0;
  }

  .command-line + .command-line {
    border-top: 1px solid #e8e8e8;
  }

  .command-text {
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
    font-size: 13px;
    color: #1a1a1a;
    word-break: break-all;
    flex: 1;
    min-width: 0;
  }

  .copy-btn {
    background: none;
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    padding: 4px 8px;
    cursor: pointer;
    color: #606060;
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
  }

  .copy-btn:hover {
    background: #e8e8e8;
    color: #030303;
  }

  .copied-feedback {
    font-size: 11px;
    color: #188038;
    font-weight: 500;
  }

  @media (max-width: 768px) {
    .clone-panel {
      min-width: 300px;
      right: -16px;
    }
  }
</style>
