import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

async function fillForm(
  page: import("@playwright/test").Page,
  bells: string,
  repeats: string,
  block: string
) {
  await page.getByLabel(/钟数/).fill(bells);
  await page.getByLabel(/重复次数/).fill(repeats);
  await page.getByLabel(/block/).fill(block);
}

test("collision: shows block order, total steps and canonical witness", async ({
  page,
}) => {
  await fillForm(page, "4", "3", "2 1 3 4");
  await page.getByRole("button", { name: "开始验真" }).click();

  await expect(page.getByTestId("result-status")).toHaveText("失败");
  await expect(page.getByTestId("result-outcome")).toHaveText(/撞回旧行/);
  await expect(page.getByTestId("fact-order")).toHaveText("2");
  await expect(page.getByTestId("fact-total")).toHaveText("3");
  await expect(page.getByTestId("witness-first")).toHaveText("0");
  await expect(page.getByTestId("witness-second")).toHaveText("2");
  await expect(page.getByTestId("witness-row")).toHaveText("1 2 3 4");
  await expect(page.getByTestId("final-row")).toHaveCount(0);
});

test("not home: only the canonical final-row evidence remains", async ({
  page,
}) => {
  await fillForm(page, "4", "1", "2 3 1 4");
  await page.getByRole("button", { name: "开始验真" }).click();

  await expect(page.getByTestId("result-status")).toHaveText("失败");
  await expect(page.getByTestId("result-outcome")).toHaveText(/未回到初始行/);
  await expect(page.getByTestId("final-row")).toContainText("2 3 1 4");
  await expect(page.getByTestId("witness")).toHaveCount(0);
});

test("pass: clean course with no repeat and rounds at step N", async ({
  page,
}) => {
  await fillForm(page, "4", "2", "2 1 3 4");
  await page.getByRole("button", { name: "开始验真" }).click();

  await expect(page.getByTestId("result-status")).toHaveText(/通过/);
  await expect(page.getByTestId("fact-order")).toHaveText("2");
  await expect(page.getByTestId("fact-total")).toHaveText("2");
  await expect(page.getByTestId("witness")).toHaveCount(0);
  await expect(page.getByTestId("final-row")).toHaveCount(0);
});

test("trillion repeats: collision decided instantly without enumeration", async ({
  page,
}) => {
  await fillForm(page, "4", "1000000000000", "2 1 3 4");
  await page.getByRole("button", { name: "开始验真" }).click();

  await expect(page.getByTestId("result-status")).toHaveText("失败");
  await expect(page.getByTestId("witness-second")).toHaveText("2");
  await expect(page.getByTestId("witness-first")).toHaveText("0");
  await expect(page.getByTestId("fact-total")).toHaveText("1,000,000,000,000");
});

test("invalid second change clears the stale result and locates block[1]", async ({
  page,
}) => {
  await fillForm(page, "4", "3", "2 1 3 4");
  await page.getByRole("button", { name: "开始验真" }).click();
  await expect(page.getByTestId("result-panel")).toBeVisible();

  const blockArea = page.getByLabel(/block/);
  await blockArea.fill("2 1 3 4\n9 9 9 9");
  await page.getByRole("button", { name: "开始验真" }).click();

  await expect(page.getByTestId("result-panel")).toHaveCount(0);
  const error = page.getByTestId("error");
  await expect(error).toBeVisible();
  await expect(error).toContainText("block[1]");
  await expect(blockArea).toBeFocused();
  // The offending line is selected in the textarea.
  const selectionStart = await blockArea.evaluate(
    (el) => (el as HTMLTextAreaElement).selectionStart
  );
  expect(selectionStart).toBe("2 1 3 4\n".length);
});

test("server-side 422 also clears the old result and reports the first bad row", async ({
  page,
}) => {
  await page.route("**/api/verify", async (route) => {
    const body = route.request().postData();
    if (body && body.includes("9")) {
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({
          error: { message: "must be a permutation", field: "block[0]" },
        }),
      });
    } else {
      await route.continue();
    }
  });

  await fillForm(page, "4", "2", "2 1 3 4");
  await page.getByRole("button", { name: "开始验真" }).click();
  await expect(page.getByTestId("result-panel")).toBeVisible();

  await page.getByLabel(/block/).fill("9 1 3 4");
  await page.getByRole("button", { name: "开始验真" }).click();

  await expect(page.getByTestId("result-panel")).toHaveCount(0);
  await expect(page.getByTestId("error")).toContainText("block[0]");
});
