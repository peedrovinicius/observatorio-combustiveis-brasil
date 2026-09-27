import pytest

import src.pipeline as pipeline_module


PIPELINE_STEPS = [
    "download_history",
    "download_open_data",
    "inspect_raw",
    "transform",
    "consolidate",
    "quality",
    "build_model",
    "station_data",
    "station_quality",
    "build_station_model",
    "analytics",
    "station_analytics",
    "reporting",
]


def test_pipeline_runs_all_steps_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    for name in PIPELINE_STEPS:
        def step(
            current: str = name,
        ) -> None:
            calls.append(current)

        monkeypatch.setattr(
            pipeline_module,
            name,
            step,
        )

    pipeline_module.main()

    assert calls == PIPELINE_STEPS


def test_pipeline_stops_after_first_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    for name in PIPELINE_STEPS:
        if name == "transform":
            def failing_step() -> None:
                calls.append("transform")
                raise RuntimeError(
                    "falha simulada"
                )

            monkeypatch.setattr(
                pipeline_module,
                name,
                failing_step,
            )
            continue

        def step(
            current: str = name,
        ) -> None:
            calls.append(current)

        monkeypatch.setattr(
            pipeline_module,
            name,
            step,
        )

    with pytest.raises(
        RuntimeError,
        match="falha simulada",
    ):
        pipeline_module.main()

    assert calls == [
        "download_history",
        "download_open_data",
        "inspect_raw",
        "transform",
    ]
