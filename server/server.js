import express from "express";
import sqlite3 from "sqlite3";
import { open } from "sqlite";
import cors from "cors";

const app = express();
app.use(cors());

app.get("/api/trends", async (req, res) => {
    const db = await open({ filename: "trends.db", driver: sqlite3.Database });
    const trends = await db.all("SELECT * FROM trends ORDER BY created_at DESC");
    res.json(trends);
});

app.listen(3001, () => console.log("API running at http://localhost:3001"));
