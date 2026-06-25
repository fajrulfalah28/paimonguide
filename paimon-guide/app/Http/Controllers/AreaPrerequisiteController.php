<?php

namespace App\Http\Controllers;

use App\Http\Requests\CheckQuestRequest;
use App\Http\Resources\AreaPrerequisiteResource;
use App\Models\AreaPrerequisite;
use Illuminate\Support\Facades\Http;

class AreaPrerequisiteController extends Controller
{
    /**
     * POST /api/check-quest
     */
    public function checkQuest(CheckQuestRequest $request)
    {
        $userInput = $request->input('area_name');

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
        }

        if (!$extractedArea) {
            return response()->json([
                'found' => false,
                'message' => "Hmm... Paimon couldn't detect any location in your message. Try asking about a location available in Genshin Impact, like \"Enkanomiya\", \"Dragonspine\", or \"The Chasm\"!",
                'ner_used' => true,
            ], 404);
        }

        $regionAreas = AreaPrerequisite::whereRaw('LOWER(region) = ?', [strtolower($extractedArea)])
            ->where('location_type', 'Area')
            ->pluck('area_name');

        if ($regionAreas->isNotEmpty()) {
            return response()->json([
                'found' => true,
                'is_region' => true,
                'region_name' => ucwords($extractedArea),
                'areas' => $regionAreas
            ]);
        }

        $query = AreaPrerequisite::query()
            ->byAreaName($extractedArea);

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
