# Plan — Reportes como herramienta de BI

**Fecha:** 2026-07-08 · **Rama:** `feature/sprint6-backlog` (LOCAL) · **Base:** 2f67f0f
**Objetivo:** evolucionar `/reportes` a una herramienta de decisiones financieras: catálogo de 4 tipos, filtros por entidad, preview enriquecida (totales + gráfica en agrupado), export PDF/XLSX acorde.

## Decisiones de alcance (aprobadas por el usuario)
- **Catálogo (dropdown único):** Ventas Detalladas, Gastos Operativos, Inventario, Estado de Resultados (Agrupado).
- **Filtros por tipo:** Ventas → Usuario/Mesero + Método de pago · Gastos → Usuario + Categoría de gasto · Inventario → (opcional) solo bajo mínimo · Estado de Resultados → Agrupar por (Día/Semana/Mes).
- **Usuario/Mesero** en Ventas = el mesero que tomó el pedido (`pedido.id_usuario`).
- **Estado de Resultados** = por bucket: Ventas, Gastos, Compras, Utilidad (= ventas−gastos−compras) + fila de totales + gráfica de barras.
- **PDF:** WeasyPrint NO ejecuta JS → la gráfica del PDF debe ser estática (CSS/SVG), no Chart.js.

## Global Constraints
- Filtros opcionales: cuando el param llega `None`, la consulta debe comportarse EXACTAMENTE como hoy (no romper). TDD que lo verifique.
- No romper tests existentes (backend 183, web 62). Cada tarea agrega tests.
- Postgres (se puede usar `date_trunc`). Chart.js solo vendor local; aplicar aprendizajes ([[web-inline-js-reserved-globals]], contenedor con altura).

## Task 1 — Backend: schemas + queries + agrupación
Filtros opcionales en detalle + endpoint agrupado + inventario como reporte. Solo backend + tests. (Ver brief.)

## Task 2 — Frontend web: formulario + preview + gráfica
Dropdown de 4 tipos, filtros condicionales por tipo, normalizador `_reporte` a 4 tipos, preview con totales (ya existe) + gráfica Chart.js en agrupado. Wrappers `api_client` para poblar dropdowns.

## Task 3 — Exportadores: PDF + XLSX
`export.py` + `print.html` para los 4 tipos (columnas + totales); gráfica ESTÁTICA (CSS/SVG) en el PDF del agrupado.

**Orden:** 1 → 2 → 3, subagent-driven, pausa de revisión con el usuario entre cada tarea.
