# Feature- Auto Schedule

as a user, I want to ability to click and 'auto schedule' button, in which the system automatically schedules the teams to the patients.

## Team is enabled for auto-scheduling
Auto Scheduling will use the Teams list to fill in a patients schedule. However, some teams should not be included in auto-Scheduling.  A team should be able to be designated as 'available for autoscheduling', and there should be an indicator/icon to represent the auto-scheduling state. (perhaps a gear icon, and the same icon with a line through it for disabled).

## Prefilled slots
A user can prefill a slot with a team and pin the slot so that it is read-only.  The auto-scheduler should take this into account and not change that slot.

## Patient Team Slot Duplicates
A team should only be booked for a patient once.  There should be no team seeing patient more than once a day.

## Team Conflict
A team can only see one patient at a time.  

## Team Priority
The teams are prioritized from top to bottom.  The auto-scheduler should respect that as much as possible.  For example, if 2 patients arrive at the same time (8:00 as an example), the system should schedule the first patient's first slot with the #1 priority team, and the second patients first slot with the #2 priority.


## Minimal Empty Gaps in Schedule
The algorithm should minimize empty gaps in a patients schedule as much as possible.
If there are no solutions, perhaps a team with multiple specialties could be split up to fill the gaps.  
