"use client";

import { useEffect, useState } from "react";
import { locationsApi } from "@/lib/api";
import type { Location } from "@/types";

export default function SettingsPage() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    locationsApi.list().then(setLocations).catch(console.error);
  }, []);

  const handleSyncLocations = async () => {
    setSyncing(true);
    setMessage("");
    try {
      const result = await locationsApi.sync();
      setMessage(`Synced ${result.synced} location(s), ${result.new} new.`);
      const updated = await locationsApi.list();
      setLocations(updated);
    } catch {
      setMessage("Failed to sync locations.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-zinc-100">Settings</h1>

      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-800 dark:text-zinc-200">Google Business Locations</h2>
          <button
            onClick={handleSyncLocations}
            disabled={syncing}
            className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {syncing ? "Syncing..." : "Sync Locations"}
          </button>
        </div>

        {message && <p className="text-sm text-green-600 dark:text-green-400">{message}</p>}

        {locations.length === 0 ? (
          <p className="text-gray-400 dark:text-zinc-500 text-sm">No locations found. Click Sync to fetch from Google.</p>
        ) : (
          <ul className="divide-y divide-gray-100 dark:divide-zinc-800">
            {locations.map((loc) => (
              <li key={loc.id} className="py-3 flex items-start gap-3">
                <span className="text-green-500 mt-0.5">✓</span>
                <div>
                  <p className="text-sm font-medium text-gray-800 dark:text-zinc-200">{loc.name}</p>
                  {loc.address && <p className="text-xs text-gray-400 dark:text-zinc-500">{loc.address}</p>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
