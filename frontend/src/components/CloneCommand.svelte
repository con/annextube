<script lang="ts">
  import { probeGitUrl } from '@/services/git-discovery';

  export let baseUrl: string;
  export let channelDir: string | null;
  export let videoFilePath: string | null;
  export let isMultiChannel: boolean;

  let gitUrl: string | null = null;
  let expanded = false;
  let activeTab: 'datalad' | 'git' = 'datalad';
  let copiedIndex: number | null = null;

  // Re-probe when channelDir changes
  let lastProbeKey = '';
  $: probeKey = `${baseUrl}|${channelDir}|${isMultiChannel}`;
  $: if (probeKey !== lastProbeKey) {
    lastProbeKey = probeKey;
    probeGit(baseUrl, channelDir, isMultiChannel);
  }

  async function probeGit(base: string, channel: string | null, multi: boolean) {
    if (multi && channel) {
      gitUrl = await probeGitUrl(`${base}/${channel}`);
      if (!gitUrl) {
        gitUrl = await probeGitUrl(base);
      }
    } else {
      gitUrl = await probeGitUrl(base);
    }
  }

  // Derive the directory name from the clone URL
  // e.g. "https://example.com/archive/.git" → "archive"
  $: dirname = gitUrl
    ? decodeURIComponent(gitUrl.replace(/\/\.git\/?$/, '').split('/').pop() || 'repo')
    : 'repo';

  // Build the video-relative path for get commands
  $: videoRelPath = (() => {
    if (!videoFilePath) return null;
    if (isMultiChannel && channelDir) {
      return `${channelDir}/videos/${videoFilePath}/`;
    }
    return `videos/${videoFilePath}/`;
  })();

  interface Command {
    text: string;
  }

  // Build commands reactively, listing all dependencies explicitly
  $: commands = buildCommands(activeTab, gitUrl, videoRelPath, dirname);

  function buildCommands(tab: 'datalad' | 'git', url: string | null, relPath: string | null, dir: string): Command[] {
    if (!url) return [];
    const cmds: Command[] = [];

    if (tab === 'datalad') {
      cmds.push({ text: `datalad clone ${url}` });
      if (relPath) {
        cmds.push({ text: `cd ${dir} && datalad get ${relPath}` });
      }
    } else {
      cmds.push({ text: `git clone ${url}` });
      if (relPath) {
        cmds.push({ text: `cd ${dir} && git annex get ${relPath}` });
      }
    }

    return cmds;
  }

  async function copyToClipboard(text: string, index: number) {
    try {
      await navigator.clipboard.writeText(text);
      copiedIndex = index;
      setTimeout(() => {
        copiedIndex = null;
      }, 1500);
    } catch {
      // Fallback: select text (clipboard API may not be available on file://)
    }
  }
</script>

{#if gitUrl}
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

        <div class="commands">
          {#each commands as cmd, i}
            <div class="command-line">
              <code class="command-text">$ {cmd.text}</code>
              <button
                class="copy-btn"
                on:click={() => copyToClipboard(cmd.text, i)}
                title="Copy to clipboard"
                aria-label="Copy command to clipboard"
              >
                {#if copiedIndex === i}
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
