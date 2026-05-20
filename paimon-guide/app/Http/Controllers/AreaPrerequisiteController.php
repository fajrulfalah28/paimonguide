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
        try {
            $nerUrl = env('NER_SERVICE_URL', 'http://127.0.0.1:5001/extract');
            if (!str_ends_with($nerUrl, '/extract')) {
                $nerUrl = rtrim($nerUrl, '/') . '/extract';
            }
            $nerResponse = Http::timeout(5)->post($nerUrl, [
                'text' => $userInput
            ]);

            if ($nerResponse->successful() && isset($nerResponse->json()['locations'])) {
                $locations = $nerResponse->json()['locations'];
                if (!empty($locations)) {
                    // Use the first resolved location
                    $extractedArea = $locations[0];
                } else {
                    $extractedArea = null;
                }
            } else {
                // Fallback to raw input if NER fails or returns nothing
                $extractedArea = $userInput;
            }
        } catch (\Exception $e) {
            // Fallback to raw input if service is down
            $extractedArea = $userInput;
        }

        if (!$extractedArea) {
            return response()->json([
                'found' => false,
                'message' => "Paimon couldn't find any recognizable locations in your message.",
            ], 404);
        }

        // 2. Query Database
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
