import { describe, expect, it } from "vitest";

import {
  addDays,
  dayOf,
  daysBetween,
  formatLongDay,
  formatPrice,
  formatTime,
  splitByNoon,
} from "./dates.js";

const ZAGREB = "Europe/Zagreb";

describe("addDays", () => {
  it("prelazi preko kraja mjeseca i godine", () => {
    expect(addDays("2026-03-31", 1)).toBe("2026-04-01");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
  });

  it("ne gubi dan pri pomicanju sata", () => {
    expect(addDays("2026-03-28", 1)).toBe("2026-03-29");
    expect(addDays("2026-03-29", 1)).toBe("2026-03-30");
    expect(addDays("2026-10-24", 2)).toBe("2026-10-26");
  });
});

describe("daysBetween", () => {
  it("uključuje oba kraja", () => {
    expect(daysBetween("2026-03-30", "2026-04-02")).toEqual([
      "2026-03-30",
      "2026-03-31",
      "2026-04-01",
      "2026-04-02",
    ]);
    expect(daysBetween("2026-03-02", "2026-03-02")).toEqual(["2026-03-02"]);
    expect(daysBetween("2026-03-03", "2026-03-02")).toEqual([]);
  });
});

describe("formatTime", () => {
  it("prikazuje vrijeme salona, a ne preglednika", () => {
    expect(formatTime("2026-03-02T08:00:00Z", ZAGREB)).toBe("09:00"); // zimsko, UTC+1
    expect(formatTime("2026-03-30T06:00:00Z", ZAGREB)).toBe("08:00"); // ljetno, UTC+2
    expect(formatTime("2026-03-02T09:00:00+01:00", ZAGREB)).toBe("09:00");
  });
});

describe("dayOf", () => {
  it("vraća lokalni dan salona i oko ponoći", () => {
    expect(dayOf("2026-03-02T22:30:00Z", ZAGREB)).toBe("2026-03-02"); // 23:30
    expect(dayOf("2026-03-02T23:30:00Z", ZAGREB)).toBe("2026-03-03"); // 00:30
  });
});

describe("splitByNoon", () => {
  it("dijeli po lokalnom satu", () => {
    const slots = ["2026-03-02T10:45:00Z", "2026-03-02T11:00:00Z", "2026-03-02T13:00:00Z"];
    expect(splitByNoon(slots, ZAGREB)).toEqual({
      morning: ["2026-03-02T10:45:00Z"], // 11:45
      afternoon: ["2026-03-02T11:00:00Z", "2026-03-02T13:00:00Z"], // 12:00 i 14:00
    });
  });
});

describe("prikaz", () => {
  it("piše dan riječima na hrvatskom", () => {
    expect(formatLongDay("2026-03-02")).toMatch(/^ponedjeljak, 2\. ožujka 2026\.?$/);
  });

  it("piše cijenu u eurima", () => {
    expect(formatPrice("15.00").replace(/\s/g, " ")).toBe("15,00 €");
  });
});
