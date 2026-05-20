<?php

namespace Database\Seeders;

use App\Models\AreaPrerequisite;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\File;

class AreaPrerequisiteSeeder extends Seeder
{
    /**
     * Seed the area_prerequisites table from genshin_areas.json.
     *
     * Structure: Region → areas → { AreaName: { type, sub_areas[] } }
     * One row per Area + one row per Sub-area.
     * Idempotent: truncates before seeding.
     */
    public function run(): void
    {
        // Truncate for idempotent re-seeding
        AreaPrerequisite::truncate();

        $jsonPath = storage_path('app/data/genshin_areas.json');

        if (!File::exists($jsonPath)) {
            $this->command->error("JSON file not found at: {$jsonPath}");
            return;
        }

        $data = json_decode(File::get($jsonPath), true);

        if (json_last_error() !== JSON_ERROR_NONE) {
            $this->command->error('Failed to parse JSON: ' . json_last_error_msg());
            return;
        }

        $rows = [];
        $now = now();

        // Quest prerequisite mappings for specific areas/sub-areas
        $questPrerequisites = [
            'Brightcrown Mountains' => json_encode(['Archon Quest Prologue: Act III', 'The Outlander Who Caught the Wind']),
            'Brightcrown Canyon' => 'Archon Quest Prologue: Act III',
            "Stormterror's Lair" => 'Archon Quest Prologue: Act III',
        ];

        foreach ($data as $regionName => $regionData) {
            $areas = $regionData['areas'] ?? [];

            foreach ($areas as $areaName => $areaData) {
                // Insert the Area itself
                $rows[] = [
                    'region' => $regionName,
                    'area_name' => $areaName,
                    'location_type' => 'Area',
                    'prerequisite_quest' => $questPrerequisites[$areaName] ?? null,
                    'created_at' => $now,
                    'updated_at' => $now,
                ];

                // Insert each Sub-area
                $subAreas = $areaData['sub_areas'] ?? [];
                foreach ($subAreas as $subAreaName) {
                    $rows[] = [
                        'region' => $regionName,
                        'area_name' => $subAreaName,
                        'location_type' => 'Sub-area',
                        'prerequisite_quest' => $questPrerequisites[$subAreaName] ?? null,
                        'created_at' => $now,
                        'updated_at' => $now,
                    ];
                }
            }
        }

        // Bulk insert in chunks for performance
        foreach (array_chunk($rows, 100) as $chunk) {
            AreaPrerequisite::insert($chunk);
        }

        $this->command->info("Seeded " . count($rows) . " area prerequisite records.");
    }
}
