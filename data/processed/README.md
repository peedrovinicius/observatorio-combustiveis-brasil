# Dados processados

Esta pasta recebe datasets gerados pelo pipeline após limpeza, tipagem, padronização e validação.

Os arquivos processados não são a fonte primária do projeto e podem ser reconstruídos a partir dos dados brutos e do código versionado.


## Substituição dos CSVs históricos

Os CSVs intermediários da série histórica são mantidos de forma idempotente por escopo.

Quando uma nova planilha válida de Brasil, regiões, estados ou municípios é transformada, os CSVs antigos daquele mesmo escopo são removidos antes da gravação das novas tabelas.

A limpeza ocorre apenas depois que a nova planilha possui pelo menos uma aba reconhecida. Uma fonte inválida não apaga a última transformação válida disponível.

Arquivos de outros escopos e saídas derivadas, como `precos_semanais_2026.csv`, não são removidos por essa rotina.
