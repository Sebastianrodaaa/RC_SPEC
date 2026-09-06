export type SourceRef = {
  file: string;
  locator: string;
  snippet: string | null;
};

export type Sourced<T = unknown> = {
  value: T | null;
  placeholder: string | null;
  source: SourceRef;
};

export type Pin = {
  label: string;
  field: Sourced;
};
