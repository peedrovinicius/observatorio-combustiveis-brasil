from __future__ import annotations

import pandas as pd


def parse_decimal_series(
    series: pd.Series,
) -> pd.Series:
    def parse(
        value: object,
    ) -> float | None:
        if pd.isna(
            value
        ):
            return None
        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            return float(
                value
            )

        text = (
            str(
                value
            )
            .strip()
            .replace(
                "R$",
                "",
            )
            .replace(
                "\u00a0",
                "",
            )
            .replace(
                " ",
                "",
            )
        )
        if not text:
            return None

        if (
            "," in text
            and "." in text
        ):
            if (
                text.rfind(
                    ","
                )
                > text.rfind(
                    "."
                )
            ):
                text = (
                    text.replace(
                        ".",
                        "",
                    )
                    .replace(
                        ",",
                        ".",
                    )
                )
            else:
                text = text.replace(
                    ",",
                    "",
                )
        elif "," in text:
            text = text.replace(
                ",",
                ".",
            )

        try:
            return float(
                text
            )
        except ValueError:
            return None

    return series.map(
        parse
    )
