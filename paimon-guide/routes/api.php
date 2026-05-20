<?php

use App\Http\Controllers\AreaPrerequisiteController;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes — Knowledge Base Lookup
|--------------------------------------------------------------------------
|
| POST /api/check-quest
| Accepts area_name (required) and region (optional).
| Returns prerequisite quest data from the knowledge base.
|
*/

Route::post('/check-quest', [AreaPrerequisiteController::class, 'checkQuest']);
