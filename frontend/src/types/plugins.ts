// types/plugins.ts
// v1.5 - Plugin and Tool type definitions.

export interface PluginInfo {
  name:        string;
  version:     string;
  description: string;
  healthy:     boolean;
  built_in:    boolean;
  loaded:      boolean;
}

export interface PluginListResponse {
  total:   number;
  plugins: PluginInfo[];
}

export interface AllToolsResponse {
  total: number;
  tools: PluginInfo[];
}

export interface ExecuteResult {
  tool:    string;
  success: boolean;
  result:  Record<string, unknown>;
}