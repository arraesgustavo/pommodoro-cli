"""
scripts/gerar_assets.py
------------------------
Gera os arquivos de audio placeholder usados pelo pommo.

Cada som e um beep sintetico com frequencia e duracao distintas,
produzido com o modulo padrao `wave` - sem dependencias externas.

Uso:
    python scripts/gerar_assets.py
"""

import math
import struct
import sys
import wave
from pathlib import Path

# Diretorio de destino dos assets de audio (raiz e pacote)
_RAIZ = Path(__file__).resolve().parent.parent
ASSETS_DIRS = [
    _RAIZ / "assets" / "sounds",
    _RAIZ / "src" / "assets" / "sounds",
]

# Definicoes de cada som gerado:
# (nome_arquivo, frequencia_hz, duracao_s, amplitude_0_a_1, descricao)
SONS: list[tuple[str, float, float, float, str]] = [
    # Fim de FOCO - dois tons ascendentes curtos, animados
    ("foco_fim.wav",         880.0, 0.18, 0.60, "Beep agudo - fim do foco"),
    ("foco_fim_2.wav",      1100.0, 0.18, 0.55, "Beep segundo tom - fim do foco"),
    # Fim de DESCANSO CURTO - tom medio suave
    ("descanso_curto_fim.wav", 523.0, 0.30, 0.45, "Beep medio - fim do descanso curto"),
    # Fim de DESCANSO LONGO - tom grave com sustain
    ("descanso_longo_fim.wav", 330.0, 0.50, 0.50, "Beep grave - fim do descanso longo"),
]

SAMPLE_RATE = 44100   # Hz
SAMPLE_WIDTH = 2      # bytes (16-bit PCM)


def _gerar_beep(
    freq: float,
    duracao: float,
    amplitude: float,
    sample_rate: int = SAMPLE_RATE,
) -> bytes:
    """
    Gera amostras PCM de uma onda senoidal com fade-in e fade-out suaves.

    Args:
        freq: Frequencia em Hz.
        duracao: Duracao em segundos.
        amplitude: Amplitude de pico (0.0 a 1.0).
        sample_rate: Taxa de amostragem em Hz.

    Returns:
        Bytes de amostras PCM little-endian 16-bit com sinal.
    """
    n_samples = int(sample_rate * duracao)
    fade_in_samp  = int(sample_rate * 0.015)   # 15ms de fade in
    fade_out_samp = int(sample_rate * 0.060)   # 60ms de fade out

    frames = bytearray()
    for i in range(n_samples):
        # Envelope - fade in
        if i < fade_in_samp:
            env = i / fade_in_samp
        # Envelope - fade out (contado do final)
        elif i >= n_samples - fade_out_samp:
            env = (n_samples - i) / fade_out_samp
        else:
            env = 1.0

        raw = amplitude * env * math.sin(2.0 * math.pi * freq * i / sample_rate)
        sample = max(-32768, min(32767, int(raw * 32767)))
        frames += struct.pack("<h", sample)

    return bytes(frames)


def gerar_arquivo(
    destino: Path,
    freq: float,
    duracao: float,
    amplitude: float,
) -> None:
    """Escreve um arquivo .wav no caminho destino."""
    pcm = _gerar_beep(freq, duracao, amplitude)
    with wave.open(str(destino), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)


def main() -> None:
    for diretorio in ASSETS_DIRS:
        diretorio.mkdir(parents=True, exist_ok=True)
        print(f"Gerando assets em: {diretorio}\n")

        for nome, freq, dur, amp, desc in SONS:
            destino = diretorio / nome
            gerar_arquivo(destino, freq, dur, amp)
            print(f"  [OK] {nome:<28} {freq:>6.0f} Hz  {dur:.2f}s  - {desc}")

    print(f"\nTotal: {len(SONS)} arquivo(s) gerado(s) em cada diretorio.")


if __name__ == "__main__":
    main()
