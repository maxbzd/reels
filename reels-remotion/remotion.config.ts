import { Config } from "@remotion/cli/config";
// Sandbox workaround: Remotion's bundled Chrome does not trust the egress proxy CA (Google Fonts fail to load),
// the system Chromium does.
if (process.env.REMOTION_BROWSER) Config.setBrowserExecutable(process.env.REMOTION_BROWSER);
