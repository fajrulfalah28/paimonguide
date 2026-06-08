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

        // ---------------------------------------------------------------
        // Quest prerequisite mappings.
        // Multiple quests are stored as newline-separated strings.
        // null = no prerequisite needed.
        // ---------------------------------------------------------------
        $questPrerequisites = [

            // === MONDSTADT ===
            'Brightcrown Mountains'     => "Archon Quest Prologue: Act III",
            'Brightcrown Canyon'        => "Archon Quest Prologue: Act III",
            "Stormterror's Lair"        => "Archon Quest Prologue: Act III",
            'Galesong Hill'             => "Archon Quest Prologue: Act I",
            'Starfell Valley'           => "Archon Quest Prologue: Act I",
            'Windwail Highland'         => "Archon Quest Prologue: Act I",
            'Dragonspine'               => "In the Mountains",
            'Windrest Peak'             => null,
            'Temple of Space'           => "A Long Day in the Mountains",
            'Apathic Interval'          => "A Long Day in the Mountains",
            'Cage of Suchness'          => "A Long Day in the Mountains",
            'Desert Pavilion'           => "A Long Day in the Mountains",
            'Luyang Academy'            => "A Long Day in the Mountains",
            'Mahavaipulya Chamber'      => "A Long Day in the Mountains",
            'Path of the Forgotten World' => "A Long Day in the Mountains",
            'Pillar Hall Central Zone'  => "A Long Day in the Mountains",

            // === LIYUE ===
            'Bishui Plain'              => "Archon Quest Chapter I: Act III\nZhongli Story Quest Act I: Sal Flore\nThe Chi of Yore",
            'Minlin'                    => "Archon Quest Chapter I: Act II",
            'Qiongji Estuary'           => null,
            'Lisha'                     => null,
            'Sea of Clouds'             => null,
            'The Chasm'                 => "The Chasm Delvers",
            'The Chasm: Underground Mines' => "The Chasm Delvers",
            'Chenyu Vale: Upper Vale'   => "Chenyu's Blessings of Sunken Jade",
            'Chenyu Vale: Southern Mountain' => "Chenyu's Blessings of Sunken Jade",
            'Mt. Laixin'                => "Chenyu's Blessings of Sunken Jade",

            // === INAZUMA ===
            'Narukami Island'           => "Sacred Sakura Cleansing Ritual",
            'Kannazuka'                 => "Tatara Tales",
            'Yashiori Island'           => "Orobashi Legacy",
            'Watatsumi Island'          => "The Moon-Bathed Deep",
            'Seirai Island'             => "Seirai Stormchasers",
            'Tsurumi Island'            => "Through the Mists",
            'Enkanomiya'               => "From Dusk to Dawn in Byakuyakoku\nErebos' Secret",

            // === SUMERU ===
            'Avidya Forest'             => "Aranyaka",
            'Lokapala Jungle'           => "Aranyaka",
            'Ardravi Valley'            => "Aranyaka",
            'Ashavan Realm'             => "Aranyaka",
            'Vissudha Field'            => "Aranyaka",
            'Vanarana'                  => "Aranyaka",
            'Lost Nursery'              => "Aranyaka",
            'Hypostyle Desert'          => "Golden Slumber\nOld Notes and New Friends",
            'Land of Lower Setekh'      => "Golden Slumber\nOld Notes and New Friends",
            'Land of Upper Setekh'      => "Golden Slumber\nOld Notes and New Friends\nAfratu's Dilemma",
            'Desert of Hadramaveth'     => "The Dirge of Bilqis",
            'Gavireh Lajavard'          => "Khavarena of Good and Evil",
            'Realm of Farakhkert'       => "Khavarena of Good and Evil",

            // === FONTAINE ===
            'Court of Fontaine Region'  => "Aqueous Tidemarks\nAnn of the Narzissenkreuz",
            'Beryl Region'              => "Aqueous Tidemarks\nAncient Colors",
            'Belleau Region'            => null,
            'Liffey Region'             => "Unfinished Comedy",
            'Fontaine Research Institute of Kinetic Energy Engineering Region' => "Fontaine Research Institute Chronicles",
            'Erinnyes Forest'           => "The Wild Fairy of Erinnyes",
            'Morte Region'              => "In the Wake of Narcissus",
            'Nostoi Region'             => "Canticles of Harmony",
            'Sea of Bygone Eras'        => "Canticles of Harmony",

            // === NATLAN ===
            'Basin of Unnumbered Flames'    => "Shadow of the Mountains\nTale of Dreams Plucked from Fire\nBetween Pledge and Forgettance\nRipe for Trouble\nTo the Night, What is the Night (Ancestral Temple)",
            'Coatepec Mountain'             => "Ripe for Trouble\nTo the Night, What is the Night (Ancestral Temple)",
            'Tequemecan Valley'             => "Between Pledge and Forgettance\nTale of Dreams Plucked from Fire\nShadow of the Mountains\nRipe for Trouble",
            'Toyac Springs'                 => "Tale of Dreams Plucked from Fire",
            'Tezcatepetonco Range'          => "City Buries By Ash\nA Dream of Gazing Upon the Distant Sky\nThe Tonatiuh Quivers\nThe Mystery of Tecoloapan Beach",
            'Quahuacan Cliff'               => "Molting Season",
            'Ochkanatlan'                   => "City Buries By Ash\nA Dream of Gazing Upon the Distant Sky\nThe Tonatiuh Quivers\nThe Lone Isle Named Night",
            'Atocpan'                       => "A Way into the Mountain\nPath to the Flaming Peaks\nInvestigator of Ancient Ruins\nThe Attack of the... Purple Tepetlisaurus\nIs \"Intensity\" Really the Key?\nSing, Ho, For the Greatness of Fat",
            'Ancient Sacred Mountain'       => "Chronicler of the Crumbling City\nSing, Ho, For the Greatness of Fat!",
            'Easybreeze Holiday Resort'     => "To a Carefree Vacation!\nTraces of Chroma\nShine On, Pipilpan Idol!",

            // === NOD-KRAI ===
            'Lempo Isle'        => "Team Rigor, or Team Intuition\nThe Tale-Telling Heart\nWhisper Beneath the Waves\nBlues of the Old World\nFriends of Moley Valley\nThe Stress of Changing Careers",
            'Hiisi Isle'        => "The Tale of the Gate Stone\nThe Mirrors, the Maze, and the Tsar\nFor a Green Island\nGift of the Mirage\nEchoes of an Unfinished Past",
            'Paha Isle'         => "Drifting Towards a Promised Sky\nPriorities First\nThe Shoemaker's Children Go Barefoot",
            'Voidsea Outlook'   => "Nightingale's Song\nReturn to Sender\nWhisper Beneath the Waves\nThe Shoemaker's Children Go Barefoot\nThe Tale-Telling Heart",
            'Wavechaser Plain'  => "Nightingale's Song\nReturn to Sender\nEchoes of a Forsaken Song\nTo Turn Each Sin Against the Sinner\nReverberation of Heroic Spirits",
            'Ashveil Peak'      => "Nightingale's Song\nReverberation of Heroic Spirits",
        ];

        foreach ($data as $regionName => $regionData) {
            $areas = $regionData['areas'] ?? [];

            foreach ($areas as $areaName => $areaData) {
                // Insert the Area itself
                $areaQuest = $questPrerequisites[$areaName] ?? null;
                $rows[] = [
                    'region'               => $regionName,
                    'area_name'            => $areaName,
                    'location_type'        => 'Area',
                    'prerequisite_quest'   => $areaQuest,
                    'created_at'           => $now,
                    'updated_at'           => $now,
                ];

                // Insert each Sub-area
                $subAreas = $areaData['sub_areas'] ?? [];
                foreach ($subAreas as $subAreaName) {
                    // If the sub-area has a specific quest in the array, use it.
                    // Otherwise, inherit the quest from the parent Area.
                    $subAreaQuest = $questPrerequisites[$subAreaName] ?? $areaQuest;
                    
                    $rows[] = [
                        'region'             => $regionName,
                        'area_name'          => $subAreaName,
                        'location_type'      => 'Sub-area',
                        'prerequisite_quest' => $subAreaQuest,
                        'created_at'         => $now,
                        'updated_at'         => $now,
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
