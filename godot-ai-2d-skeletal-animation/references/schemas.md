# Schemas

The bundled JSON Schema files document the supported v1 fields. The Python validators enforce the same practical subset without requiring external packages.

## `rig_meta.json`

Required top-level fields:

- `schema_version`: must be `"1.0"`.
- `case_id`: stable case or asset id.
- `object_type`: `humanoid`, `weapon_humanoid`, `quadruped`, `mechanical`, or `custom`.
- `skeleton.bones`: ordered or unordered list of bones.
- `parts`: transparent PNG bindings.

Bone fields:

- `name`: unique id.
- `parent`: parent bone name or `null` for the single root.
- `position`: local `[x, y]`.
- `rotation_degrees`: optional rest rotation.

Part fields:

- `id`: stable part id.
- `file`: path relative to the case folder.
- `bone`: controlling bone.
- `pivot`: pixel coordinate inside the part image.
- `offset`: local display offset from bone origin.
- `z_index`: render ordering.

Sockets are marker-like attachment points. Hitboxes use `anchor` to reference a bone or socket.

## `motion.json`

Required fields:

- `schema_version`
- `case_id`
- `animation`
- `category`: `idle`, `move`, or `action`.
- `length`
- `loop`
- `tracks`

Track fields:

- `target`: `bone` or `socket`.
- `name`: target name.
- `property`: `rotation_degrees`, `position`, or `scale`.
- `keys`: sorted keyframes with `time` and `value`.

Action animations must include on/off events. Use `hitbox_on`/`hitbox_off` for combat and `hazard_on`/`hazard_off` for traps.

## `qa_report.json`

`qa_report.json` is generated per case by the summary script and includes:

- `summary.critical`
- `summary.warning`
- `summary.info`
- `checks[]`
- `artifacts.scene`
- `artifacts.preview`
