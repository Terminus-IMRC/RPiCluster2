/*
 * Target: ATtiny13a
 * avrdude: -U lfuse:w:0x6b:m -U hfuse:w:0xf9:m
 */

#define F_CPU (128000UL / 8)
#include <avr/io.h>
#include <util/delay.h>

int main(void)
{
    /*
     * PB1 is connected to nowhere, so enable the pull-up resistor on it.
     */
    PORTB |= _BV(PORTB1);

    _delay_ms(3000);

    /*
     * PB0 is connected to #PS_ON and it's pulled up by power supply, so let it
     * down.
     */
    DDRB |= _BV(DDB0);

    /* A deep dive into an infinite loop. */
    return 0;
}
