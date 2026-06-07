# Post-merge cleanup

Архив с изменёнными файлами не умеет удалять старые каталоги автоматически.

После применения изменений вручную удалите из рабочей копии репозитория устаревшие каталоги, которые больше не являются источником истины:

- `src/stratbox/macrobanks/cbr_archiver/`
- `src/app/scenarios/`
- `src/app/resources/scenarios/`

Важно:
- текущее приложение уже работает от `app/product/*`, а не от `app/scenarios/*`;
- новый домен загрузчика файлов ЦБ живёт в `src/stratbox/macrobanks/cbr_file_collector/`.
