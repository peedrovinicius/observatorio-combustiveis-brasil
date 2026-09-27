# Dados processados

Esta pasta recebe datasets gerados pelo pipeline após limpeza, tipagem, padronização e validação.

Os arquivos processados não são a fonte primária do projeto e podem ser reconstruídos a partir dos dados brutos e do código versionado.


## Substituição dos CSVs históricos

Os CSVs intermediários da série histórica são mantidos de forma idempotente por escopo.

Na execução completa, Brasil, regiões, estados e municípios são preparados antes de qualquer substituição. Todas as abas reconhecidas são convertidas primeiro para CSVs em staging.

Somente depois de todo o lote estar pronto, os CSVs históricos anteriores e `history_transform_manifest.json` são movidos para backup temporário. Os novos CSVs e o novo manifesto são instalados juntos. Se uma gravação ou instalação falhar, os arquivos novos já instalados são removidos e o bundle anterior é restaurado.

O manifesto processado registra o hash do manifesto raw que originou a transformação e o tamanho e SHA-256 de cada CSV. A consolidação recusa arquivos alterados, extras ou gerados a partir de outro snapshot raw.

Uma planilha sem tabela reconhecível impede a substituição do lote inteiro. Arquivos derivados, como `precos_semanais_2026.csv`, e arquivos de outras camadas não são removidos por essa rotina.

Os CSVs históricos processados são derivados reconstruíveis e não devem ser editados manualmente.
