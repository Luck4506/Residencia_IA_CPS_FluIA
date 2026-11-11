# Data Dictionary: App Categorization

**File:** `app_categorization_-_app_categorization.csv`
**Rows:** 1,691
**Columns:** 5

## Columns

| Column | Type | Unique Values | Nulls | Description |
|---|---|---|---|---|
| `package_name` | string | 1,691 | 0 | Android package identifier for the app (e.g., `ai.character.app`). Unique per row. |
| `title` | string | 1,636 | 0 | Display name of the app (e.g., `Character AI`). |
| `genre` | string | 43 | 0 | Original app store genre/category label (e.g., `Lifestyle`, `Entertainment`, `Productivity`). Includes an `Unknown` value. |
| `description_snippet` | string | 1,482 | 0 | Short truncated description of the app's function (avg. ~60 characters). |
| `Category` | string | 40 | 0 | Custom hierarchical category assigned to the app, using `>` to denote sub-levels (e.g., `Work & Study > Productivity`, `Daily Life > Health > Health & Fitness`). |

## `Category` Top-Level Groups

- **Daily Life** > Auto & Vehicles, Events & Tickets, Finance, Food & Drink, Health (and sub: Health & Fitness, Medical), House & devices, Maps & Navigation, Parenting, Shopping, Travel & Local, Weather
- **Media** > Entertainment, Music & Audio, News & Magazines, Photos (and sub: Gallery, Photo editor), Video Players & Editors
- **Work & Study** > Art & Design, Books & Reference, Business, Education, Email, Gig work, Meeting, Productivity, Survey
- **To exclude** > Call, Camera, Launcher, Noninteractive apps, Special apps
- **Other top-level:** Browser, Game, Message, Others, Social, System tool
