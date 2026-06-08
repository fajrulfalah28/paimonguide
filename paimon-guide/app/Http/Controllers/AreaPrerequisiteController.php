<?php

namespace App\Http\Controllers;

use App\Http\Requests\CheckQuestRequest;
use App\Http\Resources\AreaPrerequisiteResource;
use App\Models\AreaPrerequisite;
use Illuminate\Support\Facades\Http;

class AreaPrerequisiteController extends Controller
{
    /**
     * Knowledge Base Lookup — check prerequisite quest for a given area.
     *
     * Accepts an area_name (required) which now can be a full sentence.
     * Uses the Python NER microservice to extract the location.
     *
     * POST /api/check-quest
     */
    public function checkQuest(CheckQuestRequest $request)
    {
        $userInput = $request->input('area_name');

        // 1. Call Python NER Microservice
        $extractedArea = null;
        try {
            $nerUrl = env('NER_SERVICE_URL', 'http://127.0.0.1:5001/extract');
            if (!str_ends_with($nerUrl, '/extract')) {
                $nerUrl = rtrim($nerUrl, '/') . '/extract';
            }
            $nerResponse = Http::timeout(30)->post($nerUrl, [
                'text' => $userInput
            ]);

            if ($nerResponse->successful() && isset($nerResponse->json()['locations'])) {
                $locations = $nerResponse->json()['locations'];
                if (!empty($locations)) {
                    $extractedArea = $locations[0];
                }
            }
        } catch (\Exception $e) {
            // NER service is down — return a friendly error rather than searching with raw input
        }

        if (!$extractedArea) {
            return response()->json([
                'found'    => false,
                'message'  => "Paimon couldn't recognise a location in your message. Try something like \"Enkanomiya\", \"Dragonspine\", or \"The Chasm\"!",
                'ner_used' => true,
            ], 404);
        }

        // 2. Check if the extracted name is actually a Region FIRST
        $regionAreas = AreaPrerequisite::whereRaw('LOWER(region) = ?', [strtolower($extractedArea)])
            ->where('location_type', 'Area')
            ->pluck('area_name');

        if ($regionAreas->isNotEmpty()) {
            return response()->json([
                'found'       => true,
                'is_region'   => true,
                'region_name' => ucwords($extractedArea),
                'areas'       => $regionAreas
            ]);
        }

        // 3. Query Database for Area/Sub-area
        $query = AreaPrerequisite::query()
            ->byAreaName($extractedArea);

        // Optional region filter
        if ($request->filled('region')) {
            $query->byRegion($request->input('region'));
        }

        $result = $query->first();

        if (!$result) {
            return response()->json([
                'found' => false,
                'message' => "Paimon couldn't find an area named \"{$extractedArea}\" in the knowledge base.",
            ], 404);
        }

        return new AreaPrerequisiteResource($result);
    }
}
