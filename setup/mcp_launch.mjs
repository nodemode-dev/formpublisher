import { spawn } from "node:child_process";
import { constants } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const windows = process.platform === "win32";
const launcher = join(root, windows ? "formpublisher.bat" : "formpublisher");
const args = ["mcp", ...process.argv.slice(2)];
const child = windows
  ? spawn(process.env.ComSpec || "cmd.exe", ["/d", "/s", "/c", `"${[launcher, ...args].map((a) => `"${a}"`).join(" ")}"`], { cwd: root, stdio: "inherit", windowsVerbatimArguments: true })
  : spawn(launcher, args, { cwd: root, stdio: "inherit" });

for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
  process.on(signal, () => {
    if (child.exitCode === null) child.kill(signal);
  });
}
child.on("error", (error) => {
  process.stderr.write(`formpublisher mcp: could not start ${launcher}: ${error.message}\n`);
  process.exit(1);
});
child.on("exit", (code, signal) => {
  process.exit(signal ? 128 + (constants.signals[signal] || 0) : code ?? 1);
});
