/*
 * Target: ATtiny13a
 * avrdude: -U lfuse:w:0x6b:m -U hfuse:w:0xf9:m
 */

#define F_CPU (128000UL / 8)
#include <avr/io.h>
#include <util/delay.h>

int main(void)
{
    uint16_t t;

    /* Set all pins as input.
     */
    DDRB = 0;
    /* PB[2-4] are not connected to anywhere this time, so enable the pull-up
     * resistor on it.
     */
    PORTB = _BV(PORTB2) | _BV(PORTB3) | _BV(PORTB4);

retry:
    DDRB &= ~_BV(DDB0);
    _delay_ms(5000);

    /* PB0 is connected to #PS_ON and it's pulled up by power supply, so let it
     * down.
     */
    DDRB |= _BV(DDB0);

    /* PB1 is connected to PWR_OK.
     */
    for (t = 0; ; ) {
        /* PWR_OK risetime T4<=10ms. */
        _delay_ms(11);
        if (PINB & _BV(PINB1))
            break;
        t += 11;
        if (t > 500)
            /* The power supply takes too long time to boot up, or it's already
             * down.
             */
            goto retry;
    }
    _delay_ms(11);
    /* If the power supply becomes not OK after it becomes OK, turn it off.
     */
    for (; ; )
        if (!(PINB & _BV(PINB1)))
            goto retry;

    /* A deep dive into an infinite loop. */
    return 0;
}
