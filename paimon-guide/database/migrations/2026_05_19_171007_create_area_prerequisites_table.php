<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('area_prerequisites', function (Blueprint $table) {
            $table->id();
            $table->string('region');
            $table->string('area_name');
            $table->string('location_type'); // 'Area' or 'Sub-area'
            $table->string('prerequisite_quest')->nullable();
            $table->timestamps();

            $table->unique(['region', 'area_name']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('area_prerequisites');
    }
};
