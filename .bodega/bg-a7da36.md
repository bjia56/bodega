---
created: '2026-02-02T22:45:48.850421+00:00'
id: bg-a7da36
priority: 2
status: closed
title: add 'bodega gc'
type: task
updated: '2026-02-03T11:17:57.826326+00:00'
---

## Description

add a new command, 'bodega gc', to garbage collect (delete) old closed tickets from the filesystem. this should create a single commit when running in branch mode. default tickets to delete should be 30 days old with an optional flag to specify the duration, e.g. 30d, 7d, 12h