package main

import (
	"encoding/json"
	"log"
	"math/rand"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"
)

type EquipmentReading struct {
	EquipmentID      string    `json:"equipment_id"`
	Temperature      float64   `json:"temperature"`
	Pressure         float64   `json:"pressure"`
	Vibration        float64   `json:"vibration"`
	RPM              int       `json:"rpm"`
	PowerConsumption float64   `json:"power_consumption"`
	Status           string    `json:"status"`
	Timestamp        time.Time `json:"timestamp"`
}

type EquipmentConfig struct {
	ID               string
	BaseTemp         float64
	BasePressure     float64
	BaseVibration    float64
	BaseRPM          int
	BasePower        float64
}

var equipmentList = []EquipmentConfig{
	{ID: "CNC-001", BaseTemp: 65.0, BasePressure: 3.5, BaseVibration: 0.8, BaseRPM: 12000, BasePower: 5.2},
	{ID: "CNC-002", BaseTemp: 62.0, BasePressure: 3.4, BaseVibration: 0.6, BaseRPM: 11800, BasePower: 4.9},
	{ID: "Press-001", BaseTemp: 45.0, BasePressure: 12.0, BaseVibration: 1.2, BaseRPM: 800, BasePower: 15.0},
	{ID: "Robot-001", BaseTemp: 38.0, BasePressure: 6.0, BaseVibration: 0.3, BaseRPM: 2000, BasePower: 3.5},
	{ID: "Conveyor-001", BaseTemp: 30.0, BasePressure: 1.0, BaseVibration: 0.5, BaseRPM: 500, BasePower: 2.0},
	{ID: "Pump-001", BaseTemp: 50.0, BasePressure: 8.0, BaseVibration: 0.9, BaseRPM: 2900, BasePower: 7.5},
}

var rng = rand.New(rand.NewSource(time.Now().UnixNano()))

func simulateReading(cfg EquipmentConfig) EquipmentReading {
	temp := cfg.BaseTemp + (rng.Float64()*10 - 5)
	pressure := cfg.BasePressure + (rng.Float64()*2 - 1)
	vibration := cfg.BaseVibration + (rng.Float64()*0.4 - 0.2)
	rpm := cfg.BaseRPM + rng.Intn(400) - 200
	power := cfg.BasePower + (rng.Float64()*1.0 - 0.5)

	status := "normal"
	if temp > cfg.BaseTemp+8 || pressure > cfg.BasePressure+1.2 {
		status = "warning"
	}
	if temp > cfg.BaseTemp+12 || pressure > cfg.BasePressure+2.0 {
		status = "critical"
	}

	if rng.Float64() < 0.03 {
		status = "fault"
		temp = 999
		pressure = 999
		vibration = 999
		rpm = 0
		power = 0
	}

	return EquipmentReading{
		EquipmentID:      cfg.ID,
		Temperature:      temp,
		Pressure:         pressure,
		Vibration:        vibration,
		RPM:              rpm,
		PowerConsumption: power,
		Status:           status,
		Timestamp:        time.Now(),
	}
}

func appendToFile(filename string, readings []EquipmentReading) error {
	f, err := os.OpenFile(filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()

	encoder := json.NewEncoder(f)
	for _, r := range readings {
		if err := encoder.Encode(r); err != nil {
			return err
		}
	}
	return nil
}

func collector(readings chan<- EquipmentReading, done <-chan struct{}, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			var wg sync.WaitGroup
			for _, eq := range equipmentList {
				wg.Add(1)
				go func(cfg EquipmentConfig) {
					defer wg.Done()
					reading := simulateReading(cfg)
					select {
					case readings <- reading:
					case <-done:
					}
				}(eq)
			}
			wg.Wait()
		case <-done:
			return
		}
	}
}

func batchWriter(readings <-chan EquipmentReading, done <-chan struct{}, wg *sync.WaitGroup, batchSize int, timeout time.Duration, filename string) {
	defer wg.Done()

	batch := make([]EquipmentReading, 0, batchSize)
	timer := time.NewTimer(timeout)
	timer.Stop()

	flush := func() {
		if len(batch) == 0 {
			return
		}
		if err := appendToFile(filename, batch); err != nil {
			log.Printf("Flush error: %v", err)
		} else {
			log.Printf("Flushed %d readings to %s", len(batch), filename)
		}
		batch = batch[:0]
		timer.Stop()
		select {
		case <-timer.C:
		default:
		}
	}

	for {
		select {
		case r, ok := <-readings:
			if !ok {
				flush()
				return
			}
			if len(batch) == 0 {
				timer.Reset(timeout)
			}
			batch = append(batch, r)
			if len(batch) >= batchSize {
				flush()
			}

		case <-timer.C:
			flush()

		case <-done:
			select {
			case r, ok := <-readings:
				if ok {
					batch = append(batch, r)
				}
			default:
			}
			flush()
			return
		}
	}
}

func main() {
	const (
		pollInterval  = 10 * time.Second
		batchSize     = 30
		batchTimeout  = 20 * time.Second
		channelBuffer = 100
		outputFile    = "equipment_data.jsonl"
	)

	readingsCh := make(chan EquipmentReading, channelBuffer)
	doneCh := make(chan struct{})

	var writerWg sync.WaitGroup
	writerWg.Add(1)
	go batchWriter(readingsCh, doneCh, &writerWg, batchSize, batchTimeout, outputFile)
	go collector(readingsCh, doneCh, pollInterval)

	log.Println("Starting Modbus/OPC emulation collector with batch writer")
	log.Printf("Equipment: %d, Poll interval: %v, Batch size: %d, Batch timeout: %v, Channel buffer: %d",
		len(equipmentList), pollInterval, batchSize, batchTimeout, channelBuffer)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	log.Println("Shutting down...")
	close(doneCh)
	writerWg.Wait()
	log.Println("Shutdown complete")
}
