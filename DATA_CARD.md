# Fiche de données Films et affiches

## Sources et conditions

| Entrée | Volume brut vérifié | Provenance |
| --- | ---: | --- |
| `movies_metadata.csv` | 45 466 lignes, 24 colonnes | Métadonnées TMDB diffusées dans The Movies Dataset. |
| `ratings_small.csv` | 100 004 lignes, 4 colonnes | Extrait de notes MovieLens diffusé dans le même jeu Kaggle. |
| `posters/` | 8 252 fichiers JPEG | Collection locale dont le volume et la convention de nommage concordent avec Movie Posters. |

Les 8 254 fichiers occupent 157 892 325 octets. Le fichier `data/raw.dvc` identifie leur version exacte.

- Les CSV proviennent de [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset). Les droits de réutilisation des métadonnées et des notes dépendent de leurs fournisseurs. Créditer TMDB et GroupLens et vérifier leurs conditions avant une réutilisation ou une diffusion. [Conditions TMDB](https://developer.themoviedb.org/docs/faq) · [Conditions MovieLens par version](https://grouplens.org/datasets/movielens/)
- La source probable des JPEG est [Movie Posters](https://www.kaggle.com/datasets/phiitm/movie-posters). La licence des fichiers locaux et les droits de redistribution des visuels ne sont pas établis par un manifeste fourni avec le projet. Le stockage de démonstration sert au travail local du binôme.
- La démonstration de CI utilise des données et des images synthétiques créées par le code du dépôt.

## Contrôles et préparation

- Les CSV sont lus en UTF-8. Le pipeline retire des sorties les lignes incomplètes, mal formées ou dupliquées dans les champs contrôlés. Les champs facultatifs, comme le résumé, peuvent rester vides.
- L’exécution de référence compte 104 lignes de films incomplètes et 30 doublons supplémentaires écartés. Les compteurs d’anomalies peuvent se recouper, car une ligne incomplète peut aussi avoir une date ou un identifiant invalide.
- Chaque affiche est décodée, convertie en RGB et redimensionnée à 224 × 224 pour calculer les moyennes. Les résultats conservent le chemin original, les dimensions, le format, la taille et les trois moyennes. Les pixels redimensionnés ne sont pas stockés.
- Le suffixe numérique du nom d’affiche donne un identifiant IMDb. Le lien exige une correspondance unique et une ligne de film valide. Les films sans affiche ont `has_poster=False` et les affiches sans lien sont conservées avec un statut et un motif.
- Le champ `movieId` des notes est un identifiant MovieLens. Le projet ne dispose pas du fichier de correspondance nécessaire pour le joindre aux identifiants TMDB.

## Limites et biais

- La couverture dépend du catalogue, de l’époque, de la langue et de la disponibilité des affiches. Les films appariés peuvent différer systématiquement de ceux dont l’affiche manque. Le taux observé est de 8 188 films appariés sur 45 332 films préparés.
- Les notes reflètent les utilisateurs et les films présents dans l’échantillon MovieLens. Leur distribution ne représente pas l’ensemble du public.
- Les moyennes RGB décrivent les couleurs globales. Les textes des affiches, leurs personnages et leur composition ne sont pas représentés par ces moyennes.
- Pour les futurs découpages d’apprentissage, regrouper les lignes et les affiches d’un même film par identifiant de film afin de contrôler la fuite de données.
