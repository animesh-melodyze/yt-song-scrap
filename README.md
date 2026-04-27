# yt-song-scrap
### PHASE 1 (Normal CPU based Ops)
1. Go this Channel: https://www.youtube.com/@sing2piano/videos
2. Create list, Get top 100 songs as per their global popularity ranking
3. Get songs and convert in wav
4. Find corresponding original song video (lyrical) from YT and convert them to wav
5. Create sheet of song with (name, artist, original genre, tempo, key, audio urls etc, )


### PHASE 2 (GPU based ops)
1. Use the following model to convert output of point 3 to MIDI:
https://github.com/qiuqiangkong/piano_transcription_inference

2. Use the following model to split vocals and BGM from output of point 4:
https://github.com/KimberleyJensen/Mel-Band-Roformer-Vocal-Model

-> Decision to take where should I upload these audio? Google Drive (non tech friendly, Storage Bucket R2/S3 or anythings else my musicians can download easily)
=> Save the outputs in a storage the following manner:
```
-Bucket-Name
    /song_slug
        /piano
            -Piano wav
            -Piano MIDI
        /original_song
            -Original song vocals
            -Original song backing track (BGM)
        /song_metadata 
                -Text file with
                    Song Name
                    Artist Name
                    Original Song Tempo
                    Original Song Key
                    Other relevant metadata
```