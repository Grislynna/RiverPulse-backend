export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/data") {
      const { results } = await env["backend-database-binding"].prepare(
        "SELECT timestamp, water_level, flow, latest_update FROM water_data ORDER BY timestamp DESC LIMIT 100"
      ).all();

      return new Response(JSON.stringify(results), {
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response("Worker is running");
  },

  async scheduled(event, env, ctx) {
    const url = "https://www.vkr.se/SlaHist/sla.htm"; // Real data source
    //const url = "https://grislynna.github.io/RiverPulse/dummy.html" // For testing with dummy data

    try {
      const response = await fetch(url);
      const html = await response.text();

      // Extract water level after specific <td>
      const waterLevelMatch = html.match(
        /VattennivÃ¥ nedstrÃ¶ms kraftverket, m.Ã¶.h\.<\/td>\s*<td[^>]*>([\d,\.]+)<\/td>/
      );
      const water_level = waterLevelMatch
        ? parseFloat(waterLevelMatch[1].replace(",", "."))
        : null;

      // Extract flow (second td with class)
      const flowMatches = [...html.matchAll(/<td class="tblborder pad w60 right bottom">([\d,\.]+)<\/td>/g)];
      const flow =
        flowMatches.length > 1
          ? parseFloat(flowMatches[1][1].replace(",", "."))
          : null;

      // Extract latest_update from <p class="gray">
      const latestUpdateMatch = html.match(/<p class="gray">([^<]+)<\/p>/);
      const latest_update = latestUpdateMatch
        ? latestUpdateMatch[1].trim()
        : null;

      if (water_level === null || flow === null || latest_update === null) {
        console.error("Failed to parse some data:", { water_level, flow, latest_update });
        return;
      }

      const timestamp = new Date().toISOString();

      // Insert data into D1
      await env["backend-database-binding"].prepare(
        "INSERT INTO water_data (timestamp, water_level, flow, latest_update) VALUES (?, ?, ?, ?)"
      )
        .bind(timestamp, water_level, flow, latest_update)
        .run();

      console.log("Inserted data:", { timestamp, water_level, flow, latest_update });
    } catch (e) {
      console.error("Failed to fetch or insert data:", e);
    }
  },
};