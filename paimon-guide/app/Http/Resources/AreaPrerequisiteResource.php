<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class AreaPrerequisiteResource extends JsonResource
{
    /**
     * Transform the resource into an array.
     * Consistent JSON shape for the Knowledge Base lookup response.
     */
    public function toArray(Request $request): array
    {
        $questVal = $this->prerequisite_quest;
        $quest = null;

        if ($questVal !== null) {
            $decoded = json_decode($questVal, true);
            if (json_last_error() === JSON_ERROR_NONE && (is_array($decoded) || is_object($decoded))) {
                $quest = $decoded;
            } else {
                $quest = $questVal;
            }
        }

        return [
            'found' => true,
            'region' => $this->region,
            'area_name' => $this->area_name,
            'location_type' => $this->location_type,
            'prerequisite_quest' => $quest,
        ];
    }
}
