import { describe, expect, it } from "vitest";
import { formatInr, formatPct, formatUsd } from "./utils";

describe("formatters", () => {
  it("formats usd", () => {
    expect(formatUsd(1234.5)).toBe("$1,234.50");
  });

  it("formats inr", () => {
    expect(formatInr(1234.5)).toContain("1,234.50");
  });

  it("formats signed percent", () => {
    expect(formatPct(1.25)).toBe("+1.25%");
    expect(formatPct(-2)).toBe("-2.00%");
  });
});
