package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestSimulateReading_ValidFields(t *testing.T) {
	cfg := EquipmentConfig{
		ID: "TEST-001", BaseTemp: 50, BasePressure: 5,
		BaseVibration: 1, BaseRPM: 1000, BasePower: 10,
	}
	r := simulateReading(cfg)
	if r.EquipmentID != "TEST-001" {
		t.Errorf("expected TEST-001, got %s", r.EquipmentID)
	}
	if r.Timestamp.IsZero() {
		t.Error("timestamp should not be zero")
	}
	if r.Status != "normal" && r.Status != "warning" && r.Status != "critical" && r.Status != "fault" {
		t.Errorf("unexpected status: %s", r.Status)
	}
}

func TestSimulateReading_FaultSets999(t *testing.T) {
	for i := 0; i < 200; i++ {
		cfg := EquipmentConfig{
			ID: "FAULT-TEST", BaseTemp: 50, BasePressure: 5,
			BaseVibration: 1, BaseRPM: 1000, BasePower: 10,
		}
		r := simulateReading(cfg)
		if r.Status == "fault" {
			if r.Temperature != 999 || r.Pressure != 999 || r.RPM != 0 || r.PowerConsumption != 0 {
				t.Errorf("fault row should have 999/0 values, got temp=%v press=%v rpm=%v power=%v",
					r.Temperature, r.Pressure, r.RPM, r.PowerConsumption)
			}
			return
		}
	}
}

func TestSimulateReading_ValuesInExpectedRange(t *testing.T) {
	cfg := EquipmentConfig{
		ID: "RANGE-TEST", BaseTemp: 50, BasePressure: 5,
		BaseVibration: 1, BaseRPM: 1000, BasePower: 10,
	}
	for i := 0; i < 100; i++ {
		r := simulateReading(cfg)
		if r.Status == "fault" {
			continue
		}
		if r.Temperature < cfg.BaseTemp-5 || r.Temperature > cfg.BaseTemp+12 {
			t.Errorf("temperature out of range: %.2f", r.Temperature)
		}
		if r.Pressure < cfg.BasePressure-1 || r.Pressure > cfg.BasePressure+2 {
			t.Errorf("pressure out of range: %.2f", r.Pressure)
		}
	}
}

func TestAppendToFile_JSONLines(t *testing.T) {
	dir := t.TempDir()
	fpath := filepath.Join(dir, "test.jsonl")

	readings := []EquipmentReading{
		{EquipmentID: "A", Temperature: 25.5, Pressure: 1.0, Vibration: 0.1, RPM: 100, PowerConsumption: 5, Status: "normal", Timestamp: time.Now()},
		{EquipmentID: "B", Temperature: 30.0, Pressure: 2.0, Vibration: 0.2, RPM: 200, PowerConsumption: 10, Status: "warning", Timestamp: time.Now()},
	}

	if err := appendToFile(fpath, readings); err != nil {
		t.Fatalf("appendToFile failed: %v", err)
	}

	data, err := os.ReadFile(fpath)
	if err != nil {
		t.Fatalf("read failed: %v", err)
	}

	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(lines) != 2 {
		t.Fatalf("expected 2 lines, got %d", len(lines))
	}

	for i, line := range lines {
		var r EquipmentReading
		if err := json.Unmarshal([]byte(line), &r); err != nil {
			t.Errorf("line %d invalid JSON: %v", i, err)
		}
	}

	if err := appendToFile(fpath, readings); err != nil {
		t.Fatalf("append failed: %v", err)
	}
	data2, _ := os.ReadFile(fpath)
	lines2 := strings.Split(strings.TrimSpace(string(data2)), "\n")
	if len(lines2) != 4 {
		t.Errorf("expected 4 lines after append, got %d", len(lines2))
	}
}

func TestBatchWriter_FlushesOnBatchSize(t *testing.T) {
	dir := t.TempDir()
	fpath := filepath.Join(dir, "batch.jsonl")

	ch := make(chan EquipmentReading, 20)
	var wg sync.WaitGroup
	wg.Add(1)

	go batchWriter(ch, &wg, 5, time.Hour, fpath)

	for i := 0; i < 5; i++ {
		ch <- EquipmentReading{
			EquipmentID: "BATCH", Temperature: float64(i),
			Pressure: 1, Vibration: 0.1, RPM: 100, PowerConsumption: 1,
			Status: "normal", Timestamp: time.Now(),
		}
	}
	time.Sleep(100 * time.Millisecond)
	close(ch)
	wg.Wait()

	data, _ := os.ReadFile(fpath)
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(lines) != 5 {
		t.Errorf("expected 5 lines, got %d", len(lines))
	}
}

func TestBatchWriter_FlushesOnClose(t *testing.T) {
	dir := t.TempDir()
	fpath := filepath.Join(dir, "close.jsonl")

	ch := make(chan EquipmentReading, 10)
	var wg sync.WaitGroup
	wg.Add(1)

	go batchWriter(ch, &wg, 10, time.Hour, fpath)

	for i := 0; i < 3; i++ {
		ch <- EquipmentReading{
			EquipmentID: "CLOSE", Temperature: float64(i),
			Pressure: 1, Vibration: 0.1, RPM: 100, PowerConsumption: 1,
			Status: "normal", Timestamp: time.Now(),
		}
	}
	close(ch)
	wg.Wait()

	data, _ := os.ReadFile(fpath)
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(lines) != 3 {
		t.Errorf("expected 3 lines after close, got %d", len(lines))
	}
}

func TestBatchWriter_TimeoutFlush(t *testing.T) {
	dir := t.TempDir()
	fpath := filepath.Join(dir, "timeout.jsonl")

	ch := make(chan EquipmentReading, 10)
	var wg sync.WaitGroup
	wg.Add(1)

	go batchWriter(ch, &wg, 10, 100*time.Millisecond, fpath)

	ch <- EquipmentReading{
		EquipmentID: "TIMEOUT", Temperature: 42, Pressure: 1,
		Vibration: 0.1, RPM: 100, PowerConsumption: 1,
		Status: "normal", Timestamp: time.Now(),
	}

	time.Sleep(200 * time.Millisecond)

	ch <- EquipmentReading{
		EquipmentID: "TIMEOUT2", Temperature: 43, Pressure: 1,
		Vibration: 0.1, RPM: 100, PowerConsumption: 1,
		Status: "normal", Timestamp: time.Now(),
	}
	close(ch)
	wg.Wait()

	data, _ := os.ReadFile(fpath)
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(lines) != 2 {
		t.Errorf("expected 2 lines (first from timeout, second from close), got %d", len(lines))
	}
}

func TestCollector_SendsCorrectCount(t *testing.T) {
	ch := make(chan EquipmentReading, 20)
	done := make(chan struct{})

	go collector(ch, done, 10*time.Millisecond)
	time.Sleep(15 * time.Millisecond)
	close(done)
	close(ch)

	count := 0
	for range ch {
		count++
	}
	if count != len(equipmentList) {
		t.Errorf("expected %d readings per cycle, got %d", len(equipmentList), count)
	}
}

func TestEquipmentList_AllHaveUniqueIDs(t *testing.T) {
	seen := make(map[string]bool)
	for _, eq := range equipmentList {
		if seen[eq.ID] {
			t.Errorf("duplicate equipment ID: %s", eq.ID)
		}
		seen[eq.ID] = true
	}
	if len(equipmentList) != 6 {
		t.Errorf("expected 6 equipment, got %d", len(equipmentList))
	}
}
