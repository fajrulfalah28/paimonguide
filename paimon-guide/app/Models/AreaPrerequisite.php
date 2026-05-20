<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Builder;

class AreaPrerequisite extends Model
{
    /**
     * The table associated with the model.
     */
    protected $table = 'area_prerequisites';

    /**
     * The attributes that are mass assignable.
     */
    protected $fillable = [
        'region',
        'area_name',
        'location_type',
        'prerequisite_quest',
    ];

    /**
     * Scope: case-insensitive match on area_name.
     */
    public function scopeByAreaName(Builder $query, string $name): Builder
    {
        $lower = strtolower($name);

        // Try exact match first, then partial match
        return $query->where(function ($q) use ($lower) {
            $q->whereRaw('LOWER(area_name) = ?', [$lower])
              ->orWhereRaw('LOWER(area_name) LIKE ?', ['%' . $lower . '%']);
        });
    }

    /**
     * Scope: case-insensitive match on region.
     */
    public function scopeByRegion(Builder $query, string $region): Builder
    {
        return $query->whereRaw('LOWER(region) = ?', [strtolower($region)]);
    }
}
