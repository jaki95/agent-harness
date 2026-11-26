import { CHART_STATES, type ConfigSection, RERUN_STATES, type Spec } from "../ir.ts";

export function configText(sections: ConfigSection[], extra: string[]) {
  const lines: string[] = [];
  for (const s of sections) lines.push(`${s.key} ${s.tokens.join(" ")}`);
  lines.push(...extra);
  return lines.join("\n");
}

export const boundRun = (module: string, prefix: string) =>
  [
    `---- MODULE ${prefix}Bound ----`,
    `EXTENDS ${module}`,
    `${prefix}TLC == INSTANCE TLC`,
    `${prefix}Naturals == INSTANCE Naturals`,
    `${prefix}Bound == ${prefix}Naturals!<(${prefix}TLC!TLCGet("distinct"), ${RERUN_STATES})`,
    `====`,
  ].join("\n");

export function chartRun({ module, variables, invariants }: Spec, tag: string, prefix: string) {
  const every: string[] = [];
  for (const name of invariants) every.push(`(IF ~${name} THEN {"${name}"} ELSE {}) \\cup `);
  return [
    `---- MODULE ${prefix}Run ----`,
    `EXTENDS ${module}`,
    `${prefix}TLC == INSTANCE TLC`,
    `${prefix}Naturals == INSTANCE Naturals`,
    `${prefix}Budget == ${prefix}Naturals!<=(${prefix}TLC!TLCGet("distinct"), ${CHART_STATES})`,
    `${prefix}Broken == ${every.join("")}{}`,
    `${prefix}Mark == ${prefix}Broken = {} \\/ ${prefix}TLC!PrintT(<<"${tag}", <<${variables.join(", ")}>>, ${prefix}Broken>>)`,
    `====`,
  ].join("\n");
}
