import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import { handleAnalyze } from "./src/server/api.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = Number(process.env.PORT) || 3000;

app.use(express.json());

// API Analyze Endpoint
app.post("/api/analyze", async (req: any, res: any) => {
  try {
    await handleAnalyze(req, res);
  } catch (err: any) {
    res.status(500).json({ error: err.message || String(err) });
  }
});

// Serve frontend build output
app.use(express.static(path.join(__dirname, "dist")));

// Fallback all routes to index.html for React SPA
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "dist", "index.html"));
});

app.listen(port, "0.0.0.0", () => {
  console.log(`[Lumina Server] Running on http://0.0.0.0:${port}`);
});

