from pathlib import Path

import pandas as pd
import pytest

import src.atomic_outputs as atomic_outputs
from src.atomic_outputs import (
    replace_csv_batch,
)


def _table(
    value: int,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "valor": [
                value,
            ]
        }
    )


def test_replace_csv_batch_replaces_complete_snapshot(
    tmp_path: Path,
) -> None:
    directory = (
        tmp_path
        / "analytics"
    )
    directory.mkdir()

    (
        directory
        / "antigo.csv"
    ).write_text(
        "valor\n1\n",
        encoding="utf-8",
    )
    note = (
        directory
        / "README.md"
    )
    note.write_text(
        "preservar",
        encoding="utf-8",
    )

    outputs = replace_csv_batch(
        directory,
        {
            "novo_a": _table(2),
            "novo_b": _table(3),
        },
    )

    assert {
        path.name
        for path in outputs
    } == {
        "novo_a.csv",
        "novo_b.csv",
    }
    assert not (
        directory
        / "antigo.csv"
    ).exists()
    assert note.exists()
    assert (
        pd.read_csv(
            directory
            / "novo_a.csv"
        ).loc[
            0,
            "valor",
        ]
        == 2
    )


def test_replace_csv_batch_stages_before_touching_old_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = (
        tmp_path
        / "model"
    )
    directory.mkdir()

    old = (
        directory
        / "antigo.csv"
    )
    old.write_text(
        "valor\n1\n",
        encoding="utf-8",
    )

    original_to_csv = (
        pd.DataFrame.to_csv
    )

    def failing_to_csv(
        self,
        path_or_buf=None,
        *args,
        **kwargs,
    ):
        path = Path(
            path_or_buf
        )
        if path.name == "novo_b.csv":
            raise OSError(
                "falha simulada"
            )
        return original_to_csv(
            self,
            path_or_buf,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        pd.DataFrame,
        "to_csv",
        failing_to_csv,
    )

    with pytest.raises(
        OSError,
        match="falha simulada",
    ):
        replace_csv_batch(
            directory,
            {
                "novo_a": _table(2),
                "novo_b": _table(3),
            },
        )

    assert old.exists()
    assert (
        old.read_text(
            encoding="utf-8"
        )
        == "valor\n1\n"
    )
    assert not (
        directory
        / "novo_a.csv"
    ).exists()


def test_replace_csv_batch_install_failure_restores_old_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = (
        tmp_path
        / "analytics_postos"
    )
    directory.mkdir()

    old_a = (
        directory
        / "antigo_a.csv"
    )
    old_b = (
        directory
        / "antigo_b.csv"
    )
    old_a.write_text(
        "valor\n1\n",
        encoding="utf-8",
    )
    old_b.write_text(
        "valor\n2\n",
        encoding="utf-8",
    )

    original_move = (
        atomic_outputs.shutil.move
    )

    def failing_move(
        source: str,
        destination: str,
    ):
        source_path = Path(
            source
        )
        destination_path = Path(
            destination
        )
        if (
            source_path.name
            == "novo_b.csv"
            and destination_path.parent
            == directory
        ):
            raise OSError(
                "falha simulada"
            )
        return original_move(
            source,
            destination,
        )

    monkeypatch.setattr(
        atomic_outputs.shutil,
        "move",
        failing_move,
    )

    with pytest.raises(
        OSError,
        match="falha simulada",
    ):
        replace_csv_batch(
            directory,
            {
                "novo_a": _table(3),
                "novo_b": _table(4),
            },
        )

    assert (
        old_a.read_text(
            encoding="utf-8"
        )
        == "valor\n1\n"
    )
    assert (
        old_b.read_text(
            encoding="utf-8"
        )
        == "valor\n2\n"
    )
    assert not (
        directory
        / "novo_a.csv"
    ).exists()
    assert not (
        directory
        / "novo_b.csv"
    ).exists()


def test_replace_csv_batch_rejects_empty_batch(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="Lote de CSVs vazio",
    ):
        replace_csv_batch(
            tmp_path,
            {},
        )


@pytest.mark.parametrize(
    "name",
    [
        "../fora",
        "pasta/arquivo",
        "pasta\\arquivo",
        "",
    ],
)
def test_replace_csv_batch_rejects_unsafe_names(
    tmp_path: Path,
    name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Nome de saída CSV inválido",
    ):
        replace_csv_batch(
            tmp_path,
            {
                name: _table(1),
            },
        )
