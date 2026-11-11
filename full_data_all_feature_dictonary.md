
  
# Data Dictionary

## Overview

This dataset contains Experience Sampling Method (ESM) data capturing smartphone usage behavior. Each row represents one ESM prompt during a phone usage session.

- **Rows:** 5,772
- **Columns:** 83

---

## Identifiers

| Variable | Type | Description |
|----------|------|-------------|
| esm_id_full | string | Full ESM prompt identifier |

---

## Target Variables

| Variable | Type | Description |
|----------|------|-------------|
| answer | int | ESM response, 1 = stop, 10 = continue |
| remaining_scaled | float | Scaled remaining session time (actual behavior) |
| intention_behavior_gap | float | Calculated as the difference between "remaining_scaled" and "answer" |

---

## Features 

### Temporal

| Variable | Type | Description |
|----------|------|-------------|
| esm_hour | int | Hour of ESM prompt (0-23) |
| esm_weekday | int | Day of week (0=Monday, 6=Sunday) |
| esm_is_weekend | int | Weekend indicator (1=yes) |
| esm_is_workday | int | Workday indicator (1=yes) |
| esm_time_period | string | Time period category (morning/afternoon/evening/night) |
| time_period_afternoon | bool | Afternoon indicator |
| time_period_evening | bool | Evening indicator |
| time_period_morning | bool | Morning indicator |
| time_period_night | bool | Night indicator |
| time_period_nan | bool | Missing time period |

---

### Session

| Variable | Type | Description |
|----------|------|-------------|
| session_minutes | float | Session duration up to ESM prompt (minutes) |
| time_since_unlock | float | Time elapsed since unlock |

---

### Interaction

| Variable | Type | Description |
|----------|------|-------------|
| tap_count | float | Number of tap events |
| text_edit_count | float | Number of text edit events |
| scroll_right_count | float | Number of right scroll events |
| scroll_right_distance | float | Total right scroll distance (pixels) |
| scroll_down_count | float | Number of down scroll events |
| scroll_down_distance | float | Total down scroll distance (pixels) |
| scroll_left_count | float | Number of left scroll events |
| scroll_left_distance | float | Total left scroll distance (pixels) |
| scroll_up_count | float | Number of up scroll events |
| scroll_up_distance | float | Total up scroll distance (pixels) |

---

### App Genre

| Variable | Type | Description |
|----------|------|-------------|
| genre_Browser | bool | Browser app |
| genre_Daily Life | bool | Daily life app |
| genre_Game | bool | Game app |
| genre_Media | bool | Media/entertainment app |
| genre_Message | bool | Messaging app |
| genre_Social | bool | Social media app |
| genre_System tool | bool | System tool app |
| genre_To exclude | bool | App flagged for exclusion |
| genre_Work & Study | bool | Work/study app |

---

### App Usage

| Variable | Type | Description |
|----------|------|-------------|
| app_duration | float | Duration of current app use |
| unique_apps_in_session | int | Number of unique apps used in session |
| app_switches_in_session | int | Number of app switches in session |
| app_total_duration_session | float | Total app usage duration in session |
| app_total_duration_today | float | Total app usage duration today |
| unique_apps_today | int | Number of unique apps used today |
| app_switches_today | int | Number of app switches today |

---

### Physical Activity

| Variable | Type | Description |
|----------|------|-------------|
| activity_type | float | Activity type code |
| activity_name | string | Activity type name |
| activity_in_vehicle | bool | User was in a vehicle (1=yes) |
| activity_on_bicycle | bool | User was on a bicycle (1=yes) |
| activity_running | bool | User was running (1=yes) |
| activity_still | bool | User was stationary (1=yes) |
| activity_walking | bool | User was walking (1=yes) |

---

### Screen Time

| Variable | Type | Description |
|----------|------|-------------|
| screen_time_minutes | float | Cumulative screen time today (minutes) |

---

### Historical

| Variable | Type | Description |
|----------|------|-------------|
| prev_session_avg_duration_today | float | Average duration of previous sessions today |
| prev_session_count_today | float | Number of previous sessions today |
| interval_after_last_session | float | Time since last session ended |
| last_session_duration | float | Duration of the previous session |

---

### Demographics

| Variable | Type | Description |
|----------|------|-------------|
| Age | float | Participant age (years) |
| Gender_encoded | int | Gender (encoding: [EDIT: specify mapping]) |
| Education_encoded | int | Education level (encoding: [EDIT: specify mapping]) |
| Race_Asian | int | Asian (1=yes) |
| Race_black | int | Black/African American (1=yes) |
| Race_native | int | Native American/Alaska Native (1=yes) |
| Race_others | int | Other race (1=yes) |
| Race_white | int | White (1=yes) |
| Employment_full_time | int | Full-time employed (1=yes) |
| Employment_part_time | int | Part-time employed (1=yes) |
| Employment_student | int | Student (1=yes) |
| Employment_self_employed | int | Self-employed (1=yes) |
| Employment_retired | int | Retired (1=yes) |
| Employment_homemaker | int | Homemaker (1=yes) |
| Employment_others | int | Other employment (1=yes) |

---

## Intermediate Variables (not used directly in ML)

| Variable | Type | Description |
|----------|------|-------------|
| date_4am | string | Date adjusted to 4am cutoff (for overnight sessions) |
| unlock_time | float | Timestamp when phone screen was unlocked |
| esm_time | int | Timestamp when ESM prompt was triggered |
| lock_time | float | Timestamp when phone screen was locked |
| timezone | string | Participant's timezone |
| esm_local | string | ESM time in local timezone |
| unlock_local | string | Unlock time in local timezone |
| app_at_prompt | string | App package name at ESM prompt |
| package_name | string | App package name |
| Category_L1 | string | App category (level 1) |
| remaining_time | float | Raw remaining session time |
| remaining_minutes | float | Remaining time (minutes) |
| remaining_capped | float | Remaining time, capped at threshold |
| remaining_log | float | Log-transformed remaining time |

---

## Notes

- Time units are in milliseconds unless otherwise noted
- **Target Variables**: Used as prediction targets in ML models
- **Features**: Used as input predictors in ML models
- **Intermediate Variables**: Used for data processing but not directly in ML
