# Context projections

All projections are version `1.0`, field-allowlisted and valid for 60–900
seconds. They do not expose a generic Twin object.

- Prayer: selected needs, confirmed emotion/fears, grace factors, scripture themes.
- Habit: selected goal, capacity, preferred duration, blocked intervention types,
  confirmed alternative response.
- Attention: confirmed attention reference, boundary preference, risk window and
  a constant indicating that sensitive reason text is absent.
- Calling: life-season, confirmed gift, service-experience and capacity references.
- Church: user-selected participation goal, relationship support, pastoral
  question and church-experience summary references only.
- Mission: confirmed calling direction, equipping/language/culture preparation,
  readiness and user-shared constraint references.
- Home: today's event reference, capacity, minimal safety summary, confirmed
  theme, grace reference and at most three active action references.
- Crisis routing: level and route availability only; no narrative or pending data.
- Timeline/search: current-user confirmed source references only.

User withdrawal immediately blocks future projections. The coordinator cancels
pending workflows/notifications and marks related search references excluded.
