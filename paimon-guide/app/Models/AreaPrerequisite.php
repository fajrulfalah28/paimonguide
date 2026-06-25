<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Builder;

class AreaPrerequisite extends Model
{
    protected $table = 'area_prerequisites';

    protected $fillable = [
        'region',
        'area_name',
        'location_type',
        'prerequisite_quest',
    ];

    public function scopeByAreaName(Builder $query, string $name): Builder
    {
        $lower = strtolower($name);

        return $query->where(function ($q) use ($lower) {
            $q->whereRaw('LOWER(area_name) = ?', [$lower])
                ->orWhereRaw('LOWER(area_name) LIKE ?', ['%' . $lower . '%']);
        });
    }

    public function scopeByRegion(Builder $query, string $region): Builder
    {
        return $query->whereRaw('LOWER(region) = ?', [strtolower($region)]);
    }
}
